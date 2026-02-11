import os
import sqlite3
import dropbox
from flask import Flask, render_template, request, redirect, send_file, jsonify

app = Flask(__name__)

# ==============================
# Configuration
# ==============================
DB_FILE = os.getenv("DB_FILE", "inventory.db")

DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

# ==============================
# Database
# ==============================
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                stock INTEGER NOT NULL
            )
        """)
        conn.commit()

def get_all_products():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM inventory ORDER BY id DESC").fetchall()

# ==============================
# Dropbox
# ==============================
def get_dropbox_client():
    if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN]):
        raise Exception("Dropbox environment variables missing")
    return dropbox.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET
    )

# ==============================
# Routes
# ==============================
@app.route("/")
def index():
    init_db()
    products = get_all_products()
    return render_template("index.html", products=products, search="", in_stock_only=False)

@app.route("/add", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()
    try:
        stock = int(request.form.get("stock", 0))
    except ValueError:
        stock = 0

    if not name:
        return redirect("/")

    with get_connection() as conn:
        max_id = conn.execute("SELECT MAX(id) FROM inventory").fetchone()[0] or 0
        sku = f"PROD{str(max_id + 1).zfill(3)}"
        conn.execute(
            "INSERT INTO inventory (name, sku, stock) VALUES (?, ?, ?)",
            (name, sku, stock)
        )
        conn.commit()

    return redirect("/")

@app.route("/update/<int:product_id>", methods=["POST"])
def update_product(product_id):
    try:
        stock = int(request.form.get("stock", 0))
    except ValueError:
        stock = 0

    with get_connection() as conn:
        conn.execute(
            "UPDATE inventory SET stock=? WHERE id=?",
            (stock, product_id)
        )
        conn.commit()

    return redirect("/")

@app.route("/delete/<int:product_id>")
def delete_product(product_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM inventory WHERE id=?", (product_id,))
        conn.commit()
    return redirect("/")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    in_stock_only = request.args.get("in_stock_only") == "on"

    products = get_all_products()
    filtered = [
        p for p in products
        if (query in p["name"].lower() or query in p["sku"].lower())
        and (not in_stock_only or p["stock"] > 0)
    ]
    return render_template("index.html", products=filtered, search=query, in_stock_only=in_stock_only)

# ==============================
# Dropbox Backup
# ==============================
@app.route("/save-dropbox")
def save_dropbox():
    try:
        dbx = get_dropbox_client()
        with open(DB_FILE, "rb") as f:
            dbx.files_upload(f.read(), f"/{DB_FILE}", mode=dropbox.files.WriteMode("overwrite"))
        return redirect("/")
    except Exception as e:
        return f"Dropbox save error: {str(e)}", 500

@app.route("/load-dropbox")
def load_dropbox():
    try:
        dbx = get_dropbox_client()
        _, res = dbx.files_download(f"/{DB_FILE}")
        with open(DB_FILE, "wb") as f:
            f.write(res.content)
        return redirect("/")
    except Exception as e:
        return f"Dropbox load error: {str(e)}", 500

@app.route("/download-db")
def download_db():
    if not os.path.exists(DB_FILE):
        return "Database not found", 404
    return send_file(DB_FILE, as_attachment=True)

@app.route("/upload-db", methods=["POST"])
def upload_db():
    if "file" not in request.files:
        return "No file uploaded", 400
    file = request.files["file"]
    if file.filename == "":
        return "Invalid file", 400
    file.save(DB_FILE)
    init_db()
    return redirect("/")

# ==============================
# Health Check
# ==============================
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ==============================
# Start App
# ==============================
init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
