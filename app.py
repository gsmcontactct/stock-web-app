from flask import Flask, render_template, request, redirect
import sqlite3
import dropbox
import os

app = Flask(__name__)
DB_NAME = "inventory.db"

# Dropbox credentials (set via Render environment variables)
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

def get_dropbox_client():
    if not (DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH_TOKEN):
        raise ValueError("Lipsesc credențiale Dropbox în variabilele de mediu")
    return dropbox.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET
    )

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_all():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

@app.route("/")
def index():
    init_db()
    products = get_all()
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

@app.route("/upload-db", methods=["POST"])
def upload_db():
    if "file" not in request.files:
        return "No file part", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    file.save(DB_NAME)
    init_db()
    return redirect("/")

@app.route("/download-db")
def download_db():
    return redirect("/save-dropbox")  # Just download from Dropbox

# === Dropbox routes ===
@app.route("/save-dropbox")
def save_dropbox():
    dbx = get_dropbox_client()
    with open(DB_NAME, "rb") as f:
        dbx.files_upload(f.read(), f"/{DB_NAME}", mode=dropbox.files.WriteMode("overwrite"))
    return redirect("/")

@app.route("/load-dropbox")
def load_dropbox():
    dbx = get_dropbox_client()
    metadata, res = dbx.files_download(f"/{DB_NAME}")
    with open(DB_NAME, "wb") as f:
        f.write(res.content)
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
