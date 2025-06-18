from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DB_FILE = "inventory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        stock INTEGER NOT NULL
    )""")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, sku, stock FROM inventory")
    products = c.fetchall()
    conn.close()
    return render_template("index.html", products=products)

@app.route('/add', methods=['POST'])
def add_product():
    name = request.form['name']
    sku = request.form['sku']
    stock = request.form['stock']
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO inventory (name, sku, stock) VALUES (?, ?, ?)", (name, sku, stock))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if request.method == 'POST':
        stock = request.form['stock']
        c.execute("UPDATE inventory SET stock = ? WHERE id = ?", (stock, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        c.execute("SELECT id, name, sku, stock FROM inventory WHERE id = ?", (product_id,))
        product = c.fetchone()
        conn.close()
        return render_template("edit.html", product=product)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
