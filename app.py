import os
import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from dropbox.exceptions import AuthError
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_FILE = "inventory.db"
DB_NAME = "inventory.db"

# Load Dropbox credentials from environment variables
DROPBOX_APP_KEY = os.environ.get("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.environ.get("DROPBOX_REFRESH_TOKEN")

# Initialize Dropbox client
dbx = dropbox.Dropbox(
    oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
    app_key=DROPBOX_APP_KEY,
    app_secret=DROPBOX_APP_SECRET
)

def normalize(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower().strip())

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            sku TEXT UNIQUE,
            stock INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    products = c.fetchall()
    conn.close()
    return render_template("index.html", products=products, search="", in_stock_only=False)

@app.route("/add", methods=["POST"])
def add_product():
    name = request.form.get("name").strip()
    try:
        stock = int(request.form.get("stock"))
    except:
        stock = 0
    if not name:
        return redirect(url_for("index"))
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT MAX(id) FROM inventory")
    max_id = c.fetchone()[0] or 0
    sku = f"PROD{str(max_id + 1).zfill(3)}"
    c.execute("INSERT INTO inventory (name, sku, stock) VALUES (?, ?, ?)", (name, sku, stock))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/update/<int:product_id>", methods=["POST"])
def update_product(product_id):
    try:
        stock = int(request.form.get("stock"))
    except:
        stock = 0
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE inventory SET stock=? WHERE id=?", (stock, product_id))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/delete/<int:product_id>")
def delete_product(product_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/search", methods=["GET"])
def search():
    query = normalize(request.args.get("q", ""))
    in_stock_only = request.args.get("in_stock_only") == "on"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    all_rows = c.fetchall()
    conn.close()
    filtered = [
        row for row in all_rows
        if (query in normalize(row[1]) or query in normalize(row[2]))
           and (not in_stock_only or row[3] > 0)
    ]
    return render_template("index.html", products=filtered, search=query, in_stock_only=in_stock_only)

# Dropbox upload
@app.route("/save-dropbox", methods=["POST"])
def save_dropbox():
    try:
        with open(DB_FILE, "rb") as f:
            dbx.files_upload(f.read(), f"/{DB_NAME}", mode=dropbox.files.WriteMode("overwrite"))
        flash("Baza de date a fost salvată în Dropbox ✅", "success")
    except AuthError as e:
        flash(f"Dropbox authentication error: {e}", "error")
    except Exception as e:
        flash(f"Dropbox error: {e}", "error")
    return redirect(url_for("index"))

# Dropbox download
@app.route("/load-dropbox", methods=["POST"])
def load_dropbox():
    try:
        metadata, res = dbx.files_download(f"/{DB_NAME}")
        with open(DB_FILE, "wb") as f:
            f.write(res.content)
        flash("Baza de date a fost descărcată din Dropbox ✅", "success")
    except AuthError as e:
        flash(f"Dropbox authentication error: {e}", "error")
    except Exception as e:
        flash(f"Dropbox error: {e}", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
