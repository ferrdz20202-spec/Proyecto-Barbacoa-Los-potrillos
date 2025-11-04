import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_FILE = "ventas.db"
def crear_base():
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalles_venta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_venta INTEGER,
            id_producto INTEGER,
            cantidad INTEGER,
            subtotal REAL,
            FOREIGN KEY(id_venta) REFERENCES ventas(id),
            FOREIGN KEY(id_producto) REFERENCES productos(id)
        )
    """)

    conexion.commit()
    conexion.close()

def insertar_producto(nombre, precio, stock):
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)", (nombre, precio, stock))
    conexion.commit()
    conexion.close()

def obtener_productos():
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, precio, stock FROM productos")
    datos = cursor.fetchall()
    conexion.close()
    return datos

def obtener_producto_por_id(pid):
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE id=?", (pid,))
    producto = cursor.fetchone()
    conexion.close()
    return producto

def actualizar_stock(producto_id, nueva_cantidad):
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()
    cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nueva_cantidad, producto_id))
    conexion.commit()
    conexion.close()

def registrar_venta_multiple(lista_productos):
    """
    lista_productos: [(producto_id, cantidad), ...]
    """
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()

    total_general = 0.0
    for producto_id, cantidad in lista_productos:
        cursor.execute("SELECT precio, stock, nombre FROM productos WHERE id=?", (producto_id,))
        fila = cursor.fetchone()
        if not fila:
            conexion.close()
            messagebox.showerror("Error", f"Producto con id {producto_id} no existe.")
            return False, 0.0
        precio, stock, nombre = fila
        if cantidad > stock:
            conexion.close()
            messagebox.showwarning("Stock insuficiente", f"Solo hay {stock} unidades de '{nombre}'.")
            return False, 0.0
        total_general += precio * cantidad

    cursor.execute("INSERT INTO ventas (total) VALUES (?)", (total_general,))
    venta_id = cursor.lastrowid

    for producto_id, cantidad in lista_productos:
        cursor.execute("SELECT precio FROM productos WHERE id=?", (producto_id,))
        precio = cursor.fetchone()[0]
        subtotal = precio * cantidad
        cursor.execute("""
            INSERT INTO detalles_venta (id_venta, id_producto, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
        """, (venta_id, producto_id, cantidad, subtotal))
        cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, producto_id))

    conexion.commit()
    conexion.close()
    return True, total_general

def obtener_reportes():
    conexion = sqlite3.connect(DB_FILE)
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT p.nombre, SUM(d.cantidad) as total_cant, SUM(d.subtotal) as total_sum
        FROM detalles_venta d
        JOIN productos p ON d.id_producto = p.id
        GROUP BY p.nombre
    """)
    datos = cursor.fetchall()
    conexion.close()
    return datos

def ventana_agregar_producto(parent=None):
    top = tk.Toplevel(parent) if parent else tk.Toplevel()
    top.title("Agregar Producto - Barbacoa El Potrillo")
    top.geometry("320x260")
    top.resizable(False, False)
    top.config(bg="#f7f7f7")

    tk.Label(top, text="Nombre del producto:", bg="#f7f7f7").pack(pady=(12,4))
    nombre_entry = tk.Entry(top, width=30)
    nombre_entry.pack()

    tk.Label(top, text="Precio:", bg="#f7f7f7").pack(pady=(8,4))
    precio_entry = tk.Entry(top, width=30)
    precio_entry.pack()

    tk.Label(top, text="Stock inicial:", bg="#f7f7f7").pack(pady=(8,4))
    stock_entry = tk.Entry(top, width=30)
    stock_entry.pack()

    def guardar():
        nombre = nombre_entry.get().strip()
        try:
            precio = float(precio_entry.get())
            stock = int(stock_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Precio o stock inválidos.")
            return
        if not nombre:
            messagebox.showerror("Error", "Ingresa un nombre.")
            return
        insertar_producto(nombre, precio, stock)
        messagebox.showinfo("Éxito", f"Producto '{nombre}' agregado.")
        top.destroy()

    tk.Button(top, text="Guardar producto", command=guardar, bg="#27ae60", fg="white").pack(pady=14)

def ventana_inventario(parent=None):
    top = tk.Toplevel(parent) if parent else tk.Toplevel()
    top.title("Inventario - Barbacoa El Potrillo")
    top.geometry("520x350")
    top.config(bg="#f7f7f7")

    cols = ("ID", "Producto", "Precio", "Stock")
    tree = ttk.Treeview(top, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    def cargar():
        for r in tree.get_children():
            tree.delete(r)
        for p in obtener_productos():
            tree.insert("", "end", values=(p[0], p[1], f"${p[2]:.2f}", p[3]))

    def reponer():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Selecciona", "Selecciona un producto para reponer.")
            return
        item = tree.item(sel[0])["values"]
        pid = item[0]
        nuevo = tk.simpledialog.askinteger("Reponer stock", "Cantidad a agregar:")
        if nuevo is None:
            return
        producto = obtener_producto_por_id(pid)
        if producto:
            _, nombre, _, stock = producto
            actualizar_stock(pid, stock + nuevo)
            messagebox.showinfo("Listo", f"Stock de '{nombre}' actualizado.")
            cargar()

    def editar_precio():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Selecciona", "Selecciona un producto para editar.")
            return
        item = tree.item(sel[0])["values"]
        pid = item[0]
        nuevo_precio = tk.simpledialog.askfloat("Editar precio", "Nuevo precio:")
        if nuevo_precio is None:
            return
        conexion = sqlite3.connect(DB_FILE)
        cursor = conexion.cursor()
        cursor.execute("UPDATE productos SET precio = ? WHERE id = ?", (nuevo_precio, pid))
        conexion.commit()
        conexion.close()
        messagebox.showinfo("Listo", "Precio actualizado.")
        cargar()

    btn_frame = tk.Frame(top, bg="#f7f7f7")
    btn_frame.pack(pady=(0,10))
    tk.Button(btn_frame, text="Reponer stock", command=reponer).grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Editar precio", command=editar_precio).grid(row=0, column=1, padx=6)
    tk.Button(btn_frame, text="Agregar producto", command=lambda: ventana_agregar_producto(top)).grid(row=0, column=2, padx=6)
    tk.Button(btn_frame, text="Refrescar", command=cargar).grid(row=0, column=3, padx=6)

    cargar()

def ventana_registrar_venta(parent=None):
    top = tk.Toplevel(parent) if parent else tk.Toplevel()
    top.title("Registrar Venta - Barbacoa El Potrillo")
    top.geometry("620x420")
    top.config(bg="#f7f7f7")

    productos = obtener_productos()
    opciones = [f"{p[1]} | ${p[2]:.2f} | Stock:{p[3]} (id:{p[0]})" for p in productos]

    left = tk.Frame(top, bg="#f7f7f7")
    left.pack(side="left", fill="y", padx=10, pady=10)

    tk.Label(left, text="Producto:", bg="#f7f7f7").pack(anchor="w")
    combo = ttk.Combobox(left, values=opciones, width=45)
    combo.pack(pady=6)

    tk.Label(left, text="Cantidad:", bg="#f7f7f7").pack(anchor="w")
    cantidad_entry = tk.Entry(left, width=10)
    cantidad_entry.pack(pady=6)

    tk.Label(left, text="(Seleccione y presione 'Agregar al carrito')", bg="#f7f7f7", fg="#666").pack(pady=(0,6))

    carrito = []  
    cols = ("ID", "Producto", "Precio", "Cantidad", "Subtotal")
    tree = ttk.Treeview(top, columns=cols, show="headings", height=12)
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    def agregar_al_carrito():
        sel = combo.get()
        if not sel:
            messagebox.showerror("Error", "Selecciona un producto.")
            return
        try:
            cantidad = int(cantidad_entry.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida.")
            return

        try:
            pid = int(sel.split("id:")[-1].rstrip(")"))
        except Exception:
            messagebox.showerror("Error", "No se pudo obtener el ID del producto.")
            return

        producto = obtener_producto_por_id(pid)
        if not producto:
            messagebox.showerror("Error", "Producto no encontrado.")
            return
        _, nombre, precio, stock = producto
        if cantidad > stock:
            messagebox.showwarning("Stock insuficiente", f"Solo hay {stock} unidades de '{nombre}'.")
            return

        subtotal = precio * cantidad
        carrito.append((pid, nombre, precio, cantidad, subtotal))
        refrescar_carrito()

    def refrescar_carrito():
        for r in tree.get_children():
            tree.delete(r)
        for item in carrito:
            pid, nombre, precio, cantidad, subtotal = item
            tree.insert("", "end", values=(pid, nombre, f"${precio:.2f}", cantidad, f"${subtotal:.2f}"))
        actualizar_total_lbl()

    def quitar_seleccion():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Selecciona", "Selecciona un artículo del carrito para quitar.")
            return
        idx = tree.index(sel[0])
        carrito.pop(idx)
        refrescar_carrito()

    def vaciar_carrito():
        carrito.clear()
        refrescar_carrito()

    total_var = tk.StringVar(value="$0.00")
    def actualizar_total_lbl():
        total = sum(item[4] for item in carrito)
        total_var.set(f"${total:.2f}")

    def finalizar_venta():
        if not carrito:
            messagebox.showwarning("Carrito vacío", "Agrega productos al carrito antes de finalizar.")
            return
        lista_para_guardar = [(item[0], item[3]) for item in carrito]  
        exito, total = registrar_venta_multiple(lista_para_guardar)
        if exito:
            messagebox.showinfo("Venta registrada", f"Venta registrada. Total: ${total:.2f}")
            vaciar_carrito()
            refrescar_productos_combo()
        else:
            pass

    def refrescar_productos_combo():
        productos = obtener_productos()
        opciones = [f"{p[1]} | ${p[2]:.2f} | Stock:{p[3]} (id:{p[0]})" for p in productos]
        combo.config(values=opciones)

    # Botones izquierdo
    tk.Button(left, text="Agregar al carrito", bg="#d35400", fg="white", command=agregar_al_carrito).pack(pady=(6,4), fill="x")
    tk.Button(left, text="Quitar seleccionado", command=quitar_seleccion).pack(pady=4, fill="x")
    tk.Button(left, text="Vaciar carrito", command=vaciar_carrito).pack(pady=4, fill="x")
    tk.Button(left, text="Finalizar venta", bg="#27ae60", fg="white", command=finalizar_venta).pack(pady=(12,4), fill="x")
    tk.Label(left, text="Total:", bg="#f7f7f7", font=("Arial", 12, "bold")).pack(pady=(10,0))
    tk.Label(left, textvariable=total_var, bg="#f7f7f7", font=("Arial", 14, "bold")).pack()

    refrescar_productos_combo()

def ventana_reportes(parent=None):
    top = tk.Toplevel(parent) if parent else tk.Toplevel()
    top.title("Reportes - Barbacoa El Potrillo")
    top.geometry("520x360")
    top.config(bg="#f7f7f7")

    cols = ("Producto", "Cantidad vendida", "Total ($)")
    tree = ttk.Treeview(top, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    datos = obtener_reportes()
    if not datos:
        tk.Label(top, text="No hay ventas registradas aún.", bg="#f7f7f7").pack(pady=20)
        return

    for d in datos:
        nombre, cant, total = d
        tree.insert("", "end", values=(nombre, cant, f"${total:.2f}"))

def main():
    crear_base()

    root = tk.Tk()
    root.title("Barbacoa El Potrillo")
    root.geometry("540x420")
    root.resizable(False, False)
    root.config(bg="#f7f7f7")

    tk.Label(root, text="Barbacoa El Potrillo", font=("Arial", 20, "bold"), bg="#f7f7f7", fg="#b03a2e").pack(pady=18)

    marco = tk.Frame(root, bg="#f7f7f7")
    marco.pack(pady=6)

    tk.Button(marco, text="🛒 Agregar Producto", width=22, height=2,
              bg="#d35400", fg="white", command=lambda: ventana_agregar_producto(root)).grid(row=0, column=0, padx=12, pady=10)
    tk.Button(marco, text="Registrar Venta", width=22, height=2,
              bg="#27ae60", fg="white", command=lambda: ventana_registrar_venta(root)).grid(row=1, column=0, padx=12, pady=6)
    tk.Button(marco, text="Ver Reportes", width=22, height=2,
              bg="#2980b9", fg="white", command=lambda: ventana_reportes(root)).grid(row=2, column=0, padx=12, pady=6)
    tk.Button(marco, text="Ver Inventario", width=22, height=2,
              bg="#8e44ad", fg="white", command=lambda: ventana_inventario(root)).grid(row=3, column=0, padx=12, pady=6)

    tk.Button(root, text="Salir", width=12, height=1, bg="#7f8c8d", fg="white", command=root.destroy).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
