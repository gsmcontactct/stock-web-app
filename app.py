from flask import Flask, render_template, request, redirect
import sqlite3
import os
import dropbox
from dropbox.exceptions import AuthError

app = Flask(__name__)
DB_NAME = "inventory.db"

# === Dropbox credentials from environment ===
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

# === Dropbox client ===
def get_dropbox_client():
    if not DROPBOX_APP_KEY or not DROPBOX_APP_SECRET or not DROPBOX_REFRESH_TOKEN:
        raise ValueError("Missing Dropbox credentials in environment variables")
    return dropbox.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET
    )

# === Database init ===
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            sku TEXT UNIQUE,
            stock INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === Helper to fetch all products ===
def get_all_products():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# === Routes ===
@app.route("/")
def index():
    products = get_all_products()
    return render_template("index.html", products=products, search="", in_stock_only=False)

@app.route("/add", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()
    try:
        stock = int(request.form.get("stock"))
    except:
        stock = 0
    if not name:
        return redirect("/")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT MAX(id) FROM inventory")
    max_id = c.fetchone()[0] or 0
    sku = f"PROD{str(max_id + 1).zfill(3)}"
    c.execute("INSERT INTO inventory (name, sku, stock) VALUES (?, ?, ?)", (name, sku, stock))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/update/<int:product_id>", methods=["POST"])
def update_product(product_id):
    try:
        stock = int(request.form.get("stock"))
    except:
        stock = 0
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE inventory SET stock=? WHERE id=?", (stock, product_id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:product_id>")
def delete_product(product_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").lower().strip()
    in_stock_only = request.args.get("in_stock_only") == "on"
    all_rows = get_all_products()
    filtered = [
        row for row in all_rows
        if (query in row[1].lower() or query in row[2].lower()) and (not in_stock_only or row[3] > 0)
    ]
    return render_template("index.html", products=filtered, search=query, in_stock_only=in_stock_only)

# === Dropbox upload ===
@app.route("/save-dropbox")
def save_dropbox():
    try:
        dbx = get_dropbox_client()
        with open(DB_NAME, "rb") as f:
            dbx.files_upload(f.read(), f"/{DB_NAME}", mode=dropbox.files.WriteMode.overwrite)
        return redirect("/")
    except AuthError as e:
        return f"Dropbox authentication error: {e}", 500
    except Exception as e:
        return f"Dropbox upload failed: {e}", 500

# === Dropbox download ===
@app.route("/load-dropbox")
def load_dropbox():
    try:
        dbx = get_dropbox_client()
        _, res = dbx.files_download(f"/{DB_NAME}")
        with open(DB_NAME, "wb") as f:
            f.write(res.content)
        return redirect("/")
    except AuthError as e:
        return f"Dropbox authentication error: {e}", 500
    except Exception as e:
        return f"Dropbox download failed: {e}", 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
