from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import os
import re
import dropbox

app = Flask(__name__)
DB_FILE = "inventory.db"

# ===========================
# DROPBOX CONFIG
# ===========================
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

def get_dropbox_client():
    if not DROPBOX_APP_KEY or not DROPBOX_APP_SECRET or not DROPBOX_REFRESH_TOKEN:
        raise ValueError("Lipsesc credențiale Dropbox în variabilele de mediu")
    return dropbox.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET
    )

# ===========================
# DATABASE
# ===========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
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

def normalize(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower().strip())

# ===========================
# ROUTES
# ===========================
@app.route("/")
def index():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory ORDER BY id DESC")
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
        return redirect("/")
    conn = sqlite3.connect(DB_FILE)
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE inventory SET stock=? WHERE id=?", (stock, product_id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:product_id>")
def delete_product(product_
