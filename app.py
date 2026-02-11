from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
import dropbox

app = Flask(__name__)

DB_NAME = "inventory.db"

# =========================
# Dropbox configuration
# =========================

def get_dropbox_client():
    return dropbox.Dropbox(
        oauth2_refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        app_key=os.environ["DROPBOX_APP_KEY"],
        app_secret=os.environ["DROPBOX_APP_SECRET"],
    )

# =========================
# Database helpers
# =========================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_all_products():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM inventory ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# =========================
# Routes
# =========================

@app.route("/")
def index():
    init_db()
    products = get_all_products()
    return render_template("index.html", products=products)

@app.route("/add", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()
    stock = int(request.form.get("stock", 0))

    if not name:
        return redirect("/")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM inventory")
    count = c.fetchone()[0]
    sku = f"PROD{count + 1:03d}"

    c.execute(
        "INSERT INTO inventory (name, sku, stock) VALUES (?, ?, ?)",
        (name, sku, stock)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/update/<int:product_id>", methods=["POST"])
def update_product(product_id):
    stock = int(request.form.get("stock", 0))

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

# =========================
# Local DB download/upload
# =========================

@app.route("/download-db")
def download_db():
    if not os.path.exists(DB_NAME):
        init_db()
    return send_file(DB_NAME, as_attachment=True)

@app.route("/upload-db", methods=["POST"])
def upload_db():
    if "file" not in request.files:
        return redirect("/")

    file = request.files["file"]
    if file.filename == "":
        return redirect("/")

    file.save(DB_NAME)
    init_db()
    return redirect("/")

# =========================
# Dropbox integration
# =========================

@app.route("/save-dropbox", methods=["POST"])
def save_dropbox():
    try:
        init_db()
        dbx = get_dropbox_client()

        with open(DB_NAME, "rb") as f:
            dbx.files_upload(
                f.read(),
                f"/{DB_NAME}",
                mode=dropbox.files.WriteMode.overwrite
            )

        return redirect("/")

    except Exception as e:
        print("DROPBOX UPLOAD ERROR:", e)
        return f"Dropbox error: {e}", 500

@app.route("/load-dropbox", methods=["POST"])
def load_dropbox():
    try:
        dbx = get_dropbox_client()
        _, res = dbx.files_download(f"/{DB_NAME}")

        with open(DB_NAME, "wb") as f:
            f.write(res.content)

        init_db()
        return redirect("/")

    except Exception as e:
        print("DROPBOX DOWNLOAD ERROR:", e)
        return f"Dropbox error: {e}", 500

# =========================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
