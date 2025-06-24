from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import re

app = Flask(__name__)
DB_FILE = "inventory.db"

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

if __name__ == "__main__":
    app.run(debug=True)