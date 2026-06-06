import sys
import os
import json
import requests
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from PIL import Image, ImageTk, ImageFilter

# --- Función Brújula (Para que el .exe encuentre imágenes) ---
def resolver_ruta(ruta_relativa):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.abspath("."), ruta_relativa)

API_URL = "https://TheIntercontinental.pythonanywhere.com"

RESOLUCION_INICIAL = "1280x720"
ALERTA_STOCK_INICIAL = 5
ALERTA_DIAS_CREDITO_INICIAL = 30

# Usar la carpeta del usuario para evitar problemas de permisos
CARPETA_BASE = os.path.expanduser("~")  # C:\Users\tu_usuario
CARPETA_RAIZ = os.path.join(CARPETA_BASE, "JorgeChavez_POS")
CARPETA_TICKETS_VENTAS = os.path.join(CARPETA_RAIZ, "Tickets_Ventas")
CARPETA_REPORTES_CORTES = os.path.join(CARPETA_RAIZ, "Reportes_Cortes")
CONFIG_ARCHIVO = os.path.join(CARPETA_RAIZ, "config.json")

# Imágenes
IMG_FONDO = resolver_ruta("fondo.png")
IMG_LOGO = resolver_ruta("logo_jc.png")

# Variables Globales
sede_actual_id = None
sede_actual_nombre = None
usuario_actual_nombre = "Desconocido"
carrito = []
ROL_ACTUAL = None
DEUDORES_CACHE = {}
CATALOGO_CACHE = []
USUARIOS_CACHE = []
SEDES_CACHE = []
background_image_tk = None
root = None
alerta_stock_var = None
alerta_dias_var = None

# --- Helpers ---
def cargar_configuracion():
    """Carga la configuración desde el archivo JSON"""
    global RESOLUCION_INICIAL, ALERTA_STOCK_INICIAL, ALERTA_DIAS_CREDITO_INICIAL
    
    # Crear carpetas si no existen
    for carpeta in [CARPETA_RAIZ, CARPETA_TICKETS_VENTAS, CARPETA_REPORTES_CORTES]:
        os.makedirs(carpeta, exist_ok=True)
    
    try:
        with open(CONFIG_ARCHIVO, 'r') as f:
            c = json.load(f)
            RESOLUCION_INICIAL = c.get("resolucion", "1280x720")
            ALERTA_STOCK_INICIAL = c.get("alerta_stock", 5)
            ALERTA_DIAS_CREDITO_INICIAL = c.get("alerta_dias", 30)
    except FileNotFoundError:
        # Si no existe el archivo, usar valores por defecto
        pass
    except json.JSONDecodeError as e:
        print(f"Error al leer configuración: {e}")
    except Exception as e:
        print(f"Error inesperado al cargar configuración: {e}")

def guardar_configuracion():
    """Guarda la configuración actual en el archivo JSON"""
    try:
        if root and alerta_stock_var and alerta_dias_var:
            c = {
                "resolucion": root.geometry(), 
                "alerta_stock": alerta_stock_var.get(), 
                "alerta_dias": alerta_dias_var.get()
            }
            with open(CONFIG_ARCHIVO, 'w') as f:
                json.dump(c, f, indent=4)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")

def api_get(ruta):
    """Realiza una petición GET a la API"""
    try:
        r = requests.get(f"{API_URL}{ruta}", timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error en API GET {ruta}: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado en API GET: {e}")
        return None

def api_post(ruta, datos, metodo="POST"):
    """Realiza una petición POST/PUT/DELETE a la API"""
    try:
        if metodo == "PUT":
            r = requests.put(f"{API_URL}{ruta}", json=datos, timeout=10)
        elif metodo == "DELETE":
            r = requests.delete(f"{API_URL}{ruta}", timeout=10)
        else:
            r = requests.post(f"{API_URL}{ruta}", json=datos, timeout=10)
        
        if r.status_code in [200, 201]:
            return r.json()
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error en API {metodo} {ruta}: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado en API {metodo}: {e}")
        return None

# --- Lógica Principal ---
def cambiar_sede(e=None):
    """Cambia la sede actual seleccionada"""
    global carrito
    try:
        txt = cb_sedes.get()
        if txt and "ID:" in txt:
            sid = int(txt.split("ID:")[1].replace(")", "").strip())
            nombre = txt.split(" (ID")[0].strip()
            
            if sede_actual_id and sede_actual_nombre:
                sede_actual_id.set(sid)
                sede_actual_nombre.set(nombre)
                cargar_inventario()
                carrito = []
                actualizar_carrito()
    except Exception as e:
        print(f"Error al cambiar sede: {e}")
        messagebox.showerror("Error", f"No se pudo cambiar de sede: {e}")

def cargar_sedes_gui():
    """Carga las sedes disponibles en el combobox"""
    global SEDES_CACHE
    try:
        data = api_get("/sedes")
        if data:
            SEDES_CACHE = data
            vals = [f"{s['nombre']} (ID:{s['id']})" for s in data]
            cb_sedes['values'] = vals
            
            # Seleccionar la primera sede si no hay ninguna seleccionada
            if vals and sede_actual_id and not sede_actual_id.get():
                cb_sedes.current(0)
                cambiar_sede(None)
        else:
            # Reintentar después de 2 segundos si falla
            if root:
                root.after(2000, cargar_sedes_gui)
    except Exception as e:
        print(f"Error al cargar sedes: {e}")
        if root:
            root.after(2000, cargar_sedes_gui)

def buscar_producto(event=None):
    """Busca productos en el inventario según término de búsqueda"""
    try:
        term = entry_buscar_inventario.get().strip()
        if not term:
            cargar_inventario()
            return
        
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showwarning("Advertencia", "Selecciona una sede primero")
            return
        
        data = api_post("/inventario/buscar", {
            "sede_id": sede_actual_id.get(), 
            "termino": term
        })
        
        tree_inv.delete(*tree_inv.get_children())
        
        if data and alerta_stock_var:
            umbral = alerta_stock_var.get()
            for p in data:
                tags = ('bajo',) if p.get('cantidad', 0) <= umbral else ()
                tree_inv.insert("", "end", iid=p['id'], 
                              values=(p.get('codigo_barras', ''), 
                                     p.get('id_producto', ''), 
                                     p.get('nombre', ''), 
                                     p.get('cantidad', 0), 
                                     f"${p.get('precio', 0):.2f}"), 
                              tags=tags)
    except Exception as e:
        print(f"Error al buscar producto: {e}")
        messagebox.showerror("Error", f"Error en búsqueda: {e}")

def cargar_inventario():
    """Carga el inventario completo de la sede actual"""
    try:
        if not sede_actual_id or not sede_actual_id.get():
            return
        
        data = api_get(f"/inventario/{sede_actual_id.get()}")
        
        tree_inv.delete(*tree_inv.get_children())
        tree_inv_venta.delete(*tree_inv_venta.get_children())
        
        if data and alerta_stock_var:
            umbral = alerta_stock_var.get()
            for p in data:
                tags = ('bajo',) if p.get('cantidad', 0) <= umbral else ()
                
                # Tree inventario
                tree_inv.insert("", "end", iid=p['id'], 
                              values=(p.get('codigo_barras', ''), 
                                     p.get('id_producto', ''), 
                                     p.get('nombre', ''), 
                                     p.get('cantidad', 0), 
                                     f"${p.get('precio', 0):.2f}"), 
                              tags=tags)
                
                # Tree ventas
                tree_inv_venta.insert("", "end", iid=p['id'], 
                                    values=(p.get('id_producto', ''), 
                                           p.get('nombre', ''), 
                                           p.get('cantidad', 0), 
                                           f"${p.get('precio', 0):.2f}"))
    except Exception as e:
        print(f"Error al cargar inventario: {e}")
        messagebox.showerror("Error", f"Error al cargar inventario: {e}")

# --- CATÁLOGO ---
def abrir_catalogo_maestro():
    """Abre la ventana del catálogo maestro de productos"""
    try:
        win = tk.Toplevel(root)
        win.title("Catálogo Maestro")
        win.geometry("950x600")
        
        # Filtros
        f_filter = tk.Frame(win)
        f_filter.pack(fill="x", padx=10, pady=5)
        tk.Label(f_filter, text="Marca:").pack(side="left")
        cb_marca = ttk.Combobox(f_filter, values=["Todas", "MOOD", "REIKS"], state="readonly")
        cb_marca.set("Todas")
        cb_marca.pack(side="left", padx=5)
        
        lbl_inst = tk.Label(win, text="Cargando...", font=("Arial", 10, "bold"), fg="blue")
        lbl_inst.pack(pady=5)
        
        # TreeView
        cols = ("nom", "marca", "desc", "costo", "publico")
        tree_cat = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree_cat.heading(c, text=c.capitalize())
        tree_cat.pack(fill="both", expand=True)
        
        # Botones
        f_btns = tk.Frame(win)
        f_btns.pack(pady=10)
        btn_accion = tk.Button(f_btns, text="Acción")
        btn_accion.pack(side="left", padx=10)
        
        if ROL_ACTUAL == 'admin':
            btn_editar = tk.Button(f_btns, text="✏️ EDITAR", bg="#FFCC00", 
                                 command=lambda: editar_item_catalogo(tree_cat, win))
            btn_editar.pack(side="left", padx=10)

        def filtrar_catalogo(event=None):
            """Filtra el catálogo por marca"""
            try:
                marca_sel = cb_marca.get()
                tree_cat.delete(*tree_cat.get_children())
                
                for item in CATALOGO_CACHE:
                    if marca_sel == "Todas" or item.get('marca') == marca_sel:
                        costo = f"${item.get('costo_estilista', 0):.2f}" if ROL_ACTUAL == 'admin' else "****"
                        tree_cat.insert("", "end", iid=item['id'], 
                                      values=(item.get('nombre', ''), 
                                             item.get('marca', ''), 
                                             item.get('descripcion', ''), 
                                             costo, 
                                             f"${item.get('precio_publico', 0):.2f}"))
            except Exception as e:
                print(f"Error al filtrar catálogo: {e}")

        def cargar_datos_catalogo():
            """Carga los datos del catálogo desde la API"""
            global CATALOGO_CACHE
            try:
                data = api_get("/catalogo")
                if data:
                    CATALOGO_CACHE = data
                    filtrar_catalogo()
                    
                    if ROL_ACTUAL == 'admin':
                        lbl_inst.config(text="ADMIN: Doble clic para comprar stock.")
                        btn_accion.config(text="AÑADIR STOCK", bg="orange", 
                                        command=lambda: accion_catalogo(tree_cat))
                    else:
                        lbl_inst.config(text="VENDEDOR: Doble clic para SOLICITAR stock")
                        btn_accion.config(text="SOLICITAR STOCK", bg="lightblue", 
                                        command=lambda: accion_catalogo(tree_cat))
                else:
                    lbl_inst.config(text="Error al cargar catálogo")
            except Exception as e:
                print(f"Error al cargar datos del catálogo: {e}")
                lbl_inst.config(text=f"Error: {e}")

        def editar_item_catalogo(tree, parent_win):
            """Edita un item del catálogo (solo admin)"""
            try:
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("Advertencia", "Selecciona un producto")
                    return
                
                iid = int(sel[0])
                item = next((i for i in CATALOGO_CACHE if i['id'] == iid), None)
                if not item:
                    messagebox.showerror("Error", "Producto no encontrado")
                    return
                
                ed_win = tk.Toplevel(parent_win)
                ed_win.title("Editar Producto")
                ed_win.geometry("400x300")
                
                # Campos
                tk.Label(ed_win, text="Nombre:").pack(pady=2)
                e_nom = tk.Entry(ed_win, width=40)
                e_nom.insert(0, item.get('nombre', ''))
                e_nom.pack()
                
                tk.Label(ed_win, text="Marca:").pack(pady=2)
                e_mar = tk.Entry(ed_win, width=40)
                e_mar.insert(0, item.get('marca', ''))
                e_mar.pack()
                
                tk.Label(ed_win, text="Descripción:").pack(pady=2)
                e_des = tk.Entry(ed_win, width=40)
                e_des.insert(0, item.get('descripcion', ''))
                e_des.pack()
                
                tk.Label(ed_win, text="Costo Estilista:").pack(pady=2)
                e_cos = tk.Entry(ed_win, width=40)
                e_cos.insert(0, item.get('costo_estilista', 0))
                e_cos.pack()
                
                tk.Label(ed_win, text="Precio Público:").pack(pady=2)
                e_pub = tk.Entry(ed_win, width=40)
                e_pub.insert(0, item.get('precio_publico', 0))
                e_pub.pack()
                
                def guardar():
                    try:
                        d = {
                            "id": iid,
                            "nombre": e_nom.get().strip(),
                            "marca": e_mar.get().strip(),
                            "descripcion": e_des.get().strip(),
                            "costo": float(e_cos.get()),
                            "publico": float(e_pub.get())
                        }
                        
                        if api_post("/catalogo/editar", d, metodo="PUT"):
                            messagebox.showinfo("Éxito", "Producto actualizado")
                            ed_win.destroy()
                            cargar_datos_catalogo()
                        else:
                            messagebox.showerror("Error", "No se pudo actualizar")
                    except ValueError:
                        messagebox.showerror("Error", "Verifica que los precios sean números válidos")
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al guardar: {e}")
                
                tk.Button(ed_win, text="GUARDAR", bg="lime", command=guardar).pack(pady=10)
            
            except Exception as e:
                print(f"Error al editar item: {e}")
                messagebox.showerror("Error", f"Error al editar: {e}")

        def accion_catalogo(tree):
            """Añade stock (admin) o solicita stock (vendedor)"""
            try:
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("Advertencia", "Selecciona un producto")
                    return
                
                val = tree.item(sel[0], "values")
                prod_nombre = val[0]
                
                cant = simpledialog.askinteger("Cantidad", 
                                             f"¿Cuántos '{prod_nombre}'?", 
                                             minvalue=1)
                if not cant:
                    return
                
                if ROL_ACTUAL == 'admin':
                    # Admin: añadir stock
                    res = api_post("/inventario/buscar", {
                        "sede_id": sede_actual_id.get(), 
                        "termino": prod_nombre
                    })
                    
                    id_exist = None
                    if res:
                        for p in res:
                            if p.get('nombre') == prod_nombre:
                                id_exist = p['id']
                                break
                    
                    if id_exist:
                        # Producto existe, añadir stock
                        api_post("/inventario/anadir_stock", {
                            "id": id_exist, 
                            "cantidad": cant
                        })
                    else:
                        # Producto nuevo, crearlo
                        try:
                            pp = float(val[4].replace("$", ""))
                        except:
                            pp = 0.0
                        
                        api_post("/inventario/agregar", {
                            "sede_id": sede_actual_id.get(),
                            "codigo_barras": "GEN-" + prod_nombre[:3].upper(),
                            "id_producto": prod_nombre,
                            "nombre": prod_nombre,
                            "cantidad": cant,
                            "precio": pp
                        })
                    
                    messagebox.showinfo("Éxito", "Stock añadido correctamente")
                    cargar_inventario()
                else:
                    # Vendedor: crear solicitud
                    if api_post("/solicitudes/crear", {
                        "sede_id": sede_actual_id.get(),
                        "nombre_sede": sede_actual_nombre.get(),
                        "usuario": usuario_actual_nombre,
                        "producto": prod_nombre,
                        "cantidad": cant
                    }):
                        messagebox.showinfo("Enviado", "Solicitud enviada al administrador")
                    else:
                        messagebox.showerror("Error", "No se pudo enviar la solicitud")
            
            except Exception as e:
                print(f"Error en acción catálogo: {e}")
                messagebox.showerror("Error", f"Error: {e}")

        cb_marca.bind("<<ComboboxSelected>>", filtrar_catalogo)
        tree_cat.bind("<Double-1>", lambda e: accion_catalogo(tree_cat))
        cargar_datos_catalogo()
    
    except Exception as e:
        print(f"Error al abrir catálogo: {e}")
        messagebox.showerror("Error", f"Error al abrir catálogo: {e}")

def cargar_solicitudes_pendientes(tree_sol):
    """Carga las solicitudes pendientes de stock"""
    try:
        tree_sol.delete(*tree_sol.get_children())
        data = api_get("/solicitudes/pendientes")
        
        if data:
            for s in data:
                tree_sol.insert("", "end", iid=s['id'], 
                              values=(s.get('fecha', ''), 
                                     s.get('nombre_sede', ''), 
                                     s.get('usuario', ''), 
                                     s.get('producto', ''), 
                                     s.get('cantidad', 0)))
    except Exception as e:
        print(f"Error al cargar solicitudes: {e}")

def aprobar_solicitud(tree_sol):
    """Aprueba una solicitud de stock"""
    try:
        sel = tree_sol.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona una solicitud")
            return
        
        sid = int(sel[0])
        item = tree_sol.item(sid, "values")
        
        if messagebox.askyesno("Confirmar", "¿Aprobar esta solicitud?"):
            sedes = api_get("/sedes")
            if not sedes:
                messagebox.showerror("Error", "No se pudieron cargar las sedes")
                return
            
            id_sede = next((s['id'] for s in sedes if s['nombre'] == item[1]), None)
            
            if id_sede:
                if api_post("/solicitudes/aprobar", {
                    "id_solicitud": sid,
                    "sede_id": id_sede,
                    "producto": item[3],
                    "cantidad": int(item[4])
                }):
                    messagebox.showinfo("Éxito", "Solicitud aprobada")
                    cargar_solicitudes_pendientes(tree_sol)
                else:
                    messagebox.showerror("Error", "No se pudo aprobar la solicitud")
            else:
                messagebox.showerror("Error", "No se encontró la sede")
    except Exception as e:
        print(f"Error al aprobar solicitud: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def rechazar_solicitud(tree_sol):
    """Rechaza una solicitud de stock"""
    try:
        sel = tree_sol.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona una solicitud")
            return
        
        if messagebox.askyesno("Confirmar", "¿Rechazar esta solicitud?"):
            if api_post("/solicitudes/rechazar", {"id_solicitud": int(sel[0])}):
                messagebox.showinfo("Éxito", "Solicitud rechazada")
                cargar_solicitudes_pendientes(tree_sol)
            else:
                messagebox.showerror("Error", "No se pudo rechazar la solicitud")
    except Exception as e:
        print(f"Error al rechazar solicitud: {e}")
        messagebox.showerror("Error", f"Error: {e}")

# --- SCANNER CORREGIDO ---
def scan_codigo_inv(event):
    """Escanea un código de barras en el inventario"""
    try:
        code = entry_codigo.get().strip()
        if not code:
            return
        
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showwarning("Advertencia", "Selecciona una sede primero")
            return
        
        res = api_post("/inventario/buscar_codigo", {
            "sede_id": sede_actual_id.get(), 
            "codigo_barras": code
        })
        
        # 1. Si el producto existe
        if res and "id" in res:
            if modo_super.get():
                # Modo supermercado: añadir 1 unidad
                api_post("/inventario/anadir_stock", {
                    "id": res['id'], 
                    "cantidad": 1
                })
                cargar_inventario()
                entry_codigo.delete(0, tk.END)
                entry_codigo.focus()
            else:
                # Modo normal: cargar datos en formulario
                entry_id.delete(0, tk.END)
                entry_id.insert(0, res.get('id_producto', ''))
                
                entry_nombre.delete(0, tk.END)
                entry_nombre.insert(0, res.get('nombre', ''))
                
                entry_cant.delete(0, tk.END)
                entry_cant.insert(0, res.get('cantidad', 0))
                
                entry_precio.delete(0, tk.END)
                entry_precio.insert(0, res.get('precio', 0))
        
        # 2. Si es un código NUEVO
        else:
            if modo_super.get():
                messagebox.showwarning("Atención", 
                                     "Producto NO encontrado. Desactiva 'Modo Super' para crearlo.")
                entry_codigo.delete(0, tk.END)
                entry_codigo.focus()
            else:
                messagebox.showinfo("Nuevo Producto", 
                                  "Código nuevo. Ingresa nombre y precio para guardarlo.")
                # El código ya está en el campo, mover foco al siguiente campo
                entry_id.focus()
    
    except Exception as e:
        print(f"Error al escanear código: {e}")
        messagebox.showerror("Error", f"Error al escanear: {e}")

def agregar_producto():
    """Agrega un nuevo producto al inventario"""
    try:
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showwarning("Advertencia", "Selecciona una sede primero")
            return
        
        # Validar que todos los campos estén llenos
        codigo = entry_codigo.get().strip()
        id_prod = entry_id.get().strip()
        nombre = entry_nombre.get().strip()
        cantidad = entry_cant.get().strip()
        precio = entry_precio.get().strip()
        
        if not all([codigo, id_prod, nombre, cantidad, precio]):
            messagebox.showwarning("Faltan datos", "Llena todos los campos")
            return
        
        # Validar números
        try:
            cantidad = int(cantidad)
            precio = float(precio)
        except ValueError:
            messagebox.showerror("Error", "Cantidad y precio deben ser números válidos")
            return
        
        d = {
            "sede_id": sede_actual_id.get(),
            "codigo_barras": codigo,
            "id_producto": id_prod,
            "nombre": nombre,
            "cantidad": cantidad,
            "precio": precio
        }
        
        if api_post("/inventario/agregar", d):
            messagebox.showinfo("Éxito", "Producto agregado correctamente")
            limpiar_form_inv()
            cargar_inventario()
        else:
            messagebox.showerror("Error", "No se pudo agregar el producto")
    
    except Exception as e:
        print(f"Error al agregar producto: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def editar_producto():
    """Carga los datos de un producto seleccionado en el formulario"""
    try:
        sel = tree_inv.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona un producto")
            return
        
        vals = tree_inv.item(sel[0], "values")
        
        entry_codigo.delete(0, tk.END)
        entry_codigo.insert(0, vals[0])
        
        entry_id.delete(0, tk.END)
        entry_id.insert(0, vals[1])
        
        entry_nombre.delete(0, tk.END)
        entry_nombre.insert(0, vals[2])
        
        entry_cant.delete(0, tk.END)
        entry_cant.insert(0, vals[3])
        
        entry_precio.delete(0, tk.END)
        entry_precio.insert(0, vals[4].replace("$", ""))
    
    except Exception as e:
        print(f"Error al editar producto: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def actualizar_producto_inv():
    """Actualiza los datos de un producto existente"""
    try:
        sel = tree_inv.selection()
        if not sel:
            messagebox.showwarning("Error", "Selecciona un producto de la lista")
            return
        
        # Validar campos
        codigo = entry_codigo.get().strip()
        id_prod = entry_id.get().strip()
        nombre = entry_nombre.get().strip()
        cantidad = entry_cant.get().strip()
        precio = entry_precio.get().strip()
        
        if not all([codigo, id_prod, nombre, cantidad, precio]):
            messagebox.showwarning("Faltan datos", "Llena todos los campos")
            return
        
        # Validar números
        try:
            cantidad = int(cantidad)
            precio = float(precio)
        except ValueError:
            messagebox.showerror("Error", "Cantidad y precio deben ser números válidos")
            return
        
        d = {
            "id": int(sel[0]),
            "codigo_barras": codigo,
            "id_producto": id_prod,
            "nombre": nombre,
            "cantidad": cantidad,
            "precio": precio
        }
        
        if api_post("/inventario/actualizar", d, metodo="PUT"):
            messagebox.showinfo("Éxito", "Producto actualizado correctamente")
            limpiar_form_inv()
            cargar_inventario()
        else:
            messagebox.showerror("Error", "No se pudo actualizar el producto")
    
    except Exception as e:
        print(f"Error al actualizar producto: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def eliminar_producto():
    """Elimina un producto del inventario (solo admin)"""
    try:
        if ROL_ACTUAL != 'admin':
            messagebox.showerror("Acceso Denegado", "Solo administradores pueden eliminar productos")
            return
        
        sel = tree_inv.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona un producto")
            return
        
        if messagebox.askyesno("Confirmar", "¿Estás seguro de borrar este producto?"):
            try:
                requests.delete(f"{API_URL}/inventario/eliminar/{sel[0]}", timeout=10)
                messagebox.showinfo("Éxito", "Producto eliminado")
                cargar_inventario()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")
    
    except Exception as e:
        print(f"Error al eliminar producto: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def limpiar_form_inv():
    """Limpia todos los campos del formulario de inventario"""
    try:
        for e in [entry_codigo, entry_id, entry_nombre, entry_cant, entry_precio]:
            e.delete(0, tk.END)
        entry_codigo.focus()
    except Exception as e:
        print(f"Error al limpiar formulario: {e}")

def transferir_stock():
    """Transfiere stock entre sedes (solo admin)"""
    try:
        if ROL_ACTUAL != 'admin':
            messagebox.showerror("Acceso Denegado", "Solo administradores pueden transferir stock")
            return
        
        sel = tree_inv.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona un producto")
            return
        
        p = tree_inv.item(sel[0], "values")
        pid = int(sel[0])
        
        data = api_get("/sedes")
        if not data:
            messagebox.showerror("Error", "No se pudieron cargar las sedes")
            return
        
        otros = [s['nombre'] for s in data if s['id'] != sede_actual_id.get()]
        
        if not otros:
            messagebox.showinfo("Info", "No hay otras sedes disponibles")
            return
        
        win = tk.Toplevel(root)
        win.title("Transferir Stock")
        win.geometry("300x200")
        
        tk.Label(win, text="Sede destino:").pack(pady=5)
        cb = ttk.Combobox(win, values=otros, state="readonly")
        cb.pack(pady=5)
        
        tk.Label(win, text="Cantidad:").pack(pady=5)
        sp = tk.Spinbox(win, from_=1, to=int(p[3]))
        sp.pack(pady=5)
        
        def confirmar():
            try:
                if not cb.get():
                    messagebox.showwarning("Advertencia", "Selecciona una sede")
                    return
                
                dest_id = next((s['id'] for s in data if s['nombre'] == cb.get()), None)
                if not dest_id:
                    messagebox.showerror("Error", "Sede no encontrada")
                    return
                
                cant = int(sp.get())
                if cant <= 0:
                    messagebox.showwarning("Advertencia", "Cantidad debe ser mayor a 0")
                    return
                
                if api_post("/inventario/transferir", {
                    "producto_matriz_id": pid,
                    "id_producto": p[1],
                    "nombre": p[2],
                    "codigo_barras": p[0],
                    "precio": float(p[4].replace("$", "")),
                    "cantidad": cant,
                    "sede_destino_id": dest_id
                }):
                    messagebox.showinfo("Éxito", "Stock transferido correctamente")
                    win.destroy()
                    cargar_inventario()
                else:
                    messagebox.showerror("Error", "No se pudo transferir el stock")
            
            except Exception as e:
                messagebox.showerror("Error", f"Error en transferencia: {e}")
        
        tk.Button(win, text="TRANSFERIR", bg="lime", command=confirmar).pack(pady=10)
    
    except Exception as e:
        print(f"Error al transferir stock: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def scan_venta(event):
    """Escanea un producto para agregarlo al carrito de venta"""
    global carrito
    try:
        code = e_scan_venta.get().strip()
        if not code:
            return
        
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showwarning("Advertencia", "Selecciona una sede primero")
            e_scan_venta.delete(0, tk.END)
            return
        
        res = api_post("/inventario/buscar_codigo", {
            "sede_id": sede_actual_id.get(), 
            "codigo_barras": code
        })
        
        if res and "id" in res:
            if res.get('cantidad', 0) > 0:
                # Buscar si ya está en el carrito
                exist = next((x for x in carrito if x['id'] == res['id']), None)
                
                if exist:
                    exist['cantidad'] += 1
                else:
                    carrito.append({
                        "id": res['id'],
                        "id_producto": res.get('id_producto', ''),
                        "nombre": res.get('nombre', ''),
                        "cantidad": 1,
                        "precio": res.get('precio', 0)
                    })
                
                actualizar_carrito()
            else:
                messagebox.showwarning("Sin Stock", "No hay unidades disponibles de este producto")
        else:
            messagebox.showwarning("No encontrado", "Producto no encontrado")
        
        e_scan_venta.delete(0, tk.END)
    
    except Exception as e:
        print(f"Error al escanear en venta: {e}")
        messagebox.showerror("Error", f"Error: {e}")
        e_scan_venta.delete(0, tk.END)

def anadir_manual_venta():
    """Añade un producto manualmente al carrito desde la lista"""
    global carrito
    try:
        sel = tree_inv_venta.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona un producto")
            return
        
        pid = int(sel[0])
        vals = tree_inv_venta.item(sel[0], "values")
        
        stock_disponible = int(vals[2])
        if stock_disponible <= 0:
            messagebox.showwarning("Sin Stock", "No hay unidades disponibles")
            return
        
        cant = simpledialog.askinteger("Cantidad", 
                                       "Cantidad a agregar:", 
                                       minvalue=1, 
                                       maxvalue=stock_disponible)
        if not cant:
            return
        
        # Buscar si ya está en el carrito
        exist = next((x for x in carrito if x['id'] == pid), None)
        
        if exist:
            exist['cantidad'] += cant
        else:
            carrito.append({
                "id": pid,
                "id_producto": vals[0],
                "nombre": vals[1],
                "cantidad": cant,
                "precio": float(vals[3].replace("$", ""))
            })
        
        actualizar_carrito()
    
    except Exception as e:
        print(f"Error al añadir manual: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def quitar_carrito():
    """Quita un producto del carrito"""
    global carrito
    try:
        sel = tree_cart.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona un producto del carrito")
            return
        
        nombre_producto = tree_cart.item(sel[0], "values")[0]
        carrito = [c for c in carrito if c['nombre'] != nombre_producto]
        actualizar_carrito()
    
    except Exception as e:
        print(f"Error al quitar del carrito: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def actualizar_carrito():
    """Actualiza la visualización del carrito"""
    try:
        tree_cart.delete(*tree_cart.get_children())
        total = 0
        
        for i in carrito:
            sub = i['cantidad'] * i['precio']
            total += sub
            tree_cart.insert("", "end", 
                           values=(i['nombre'], 
                                  i['cantidad'], 
                                  f"${i['precio']:.2f}", 
                                  f"${sub:.2f}"))
        
        lbl_total.config(text=f"Total: ${total:.2f}")
    
    except Exception as e:
        print(f"Error al actualizar carrito: {e}")

def finalizar_venta():
    """Finaliza la venta actual"""
    try:
        if not carrito:
            messagebox.showwarning("Carrito vacío", "Agrega productos antes de finalizar")
            return
        
        # Preguntar tipo de venta
        tipo = messagebox.askyesnocancel("Tipo de Pago", 
                                        "¿Venta a Crédito?\n\nSí = Crédito\nNo = Contado")
        if tipo is None:
            return
        
        tipo_str = "credito" if tipo else "contado"
        
        if tipo:
            # Venta a crédito: seleccionar o crear cliente
            win = tk.Toplevel(root)
            win.title("Seleccionar Cliente")
            win.geometry("400x300")
            
            tk.Label(win, text="Selecciona un cliente:").pack(pady=5)
            lb = tk.Listbox(win, width=50)
            lb.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Cargar deudores
            data = api_get(f"/deudores/{sede_actual_id.get()}")
            if data:
                for d in data:
                    lb.insert(tk.END, d['nombre'])
            
            f_btns = tk.Frame(win)
            f_btns.pack(pady=10)
            
            def usar_existente():
                sel = lb.curselection()
                if not sel:
                    messagebox.showwarning("Advertencia", "Selecciona un cliente")
                    return
                procesar(tipo_str, lb.get(sel[0]))
                win.destroy()
            
            def crear_nuevo():
                nom = simpledialog.askstring("Nuevo Cliente", "Nombre del cliente:")
                if nom and nom.strip():
                    procesar(tipo_str, nom.strip())
                    win.destroy()
            
            tk.Button(f_btns, text="Usar Seleccionado", bg="lightblue", 
                     command=usar_existente).pack(side="left", padx=5)
            tk.Button(f_btns, text="Crear Nuevo", bg="lightgreen", 
                     command=crear_nuevo).pack(side="left", padx=5)
        else:
            # Venta de contado
            procesar("contado", None)
    
    except Exception as e:
        print(f"Error al finalizar venta: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def procesar(tipo, deudor):
    """Procesa y registra la venta"""
    global carrito
    try:
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showerror("Error", "No hay sede seleccionada")
            return
        
        datos = {
            "sede_id": sede_actual_id.get(),
            "carrito": carrito,
            "tipo_venta": tipo,
            "nombre_deudor": deudor
        }
        
        if api_post("/ventas/finalizar", datos):
            imprimir_ticket_venta(tipo, deudor)
            messagebox.showinfo("Venta Exitosa", "Venta registrada correctamente")
            carrito = []
            actualizar_carrito()
            cargar_inventario()
            cargar_deudores()
        else:
            messagebox.showerror("Error", "No se pudo registrar la venta")
    
    except Exception as e:
        print(f"Error al procesar venta: {e}")
        messagebox.showerror("Error", f"Error al procesar: {e}")

def imprimir_ticket_venta(tipo, deudor):
    """Genera e imprime el ticket de venta en PDF"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(CARPETA_TICKETS_VENTAS, f"ticket_{timestamp}.pdf")
        
        # Crear PDF
        c = canvas.Canvas(path, pagesize=(165, 800))
        centro_x = 165 / 2
        y = 780
        
        # Logo
        if os.path.exists(IMG_LOGO):
            try:
                c.drawImage(IMG_LOGO, x=22.5, y=y-60, width=120, height=60, 
                          preserveAspectRatio=True, mask='auto')
                y -= 75
            except:
                c.setFont("Helvetica-Bold", 12)
                c.drawCentredString(centro_x, y, "JORGE CHAVEZ")
                y -= 20
        else:
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(centro_x, y, "JORGE CHAVEZ")
            y -= 20
        
        # Encabezado
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(centro_x, y, "DISTRIBUIDOR")
        y -= 15
        
        # Línea separadora
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.line(10, y, 155, y)
        y -= 15
        
        # Información de venta
        c.setFont("Helvetica", 9)
        c.drawString(10, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 12
        c.drawString(10, y, f"Cliente: {deudor or 'Mostrador'}")
        y -= 12
        c.drawString(10, y, f"Pago: {tipo.upper()}")
        y -= 15
        
        # Línea separadora
        c.line(10, y, 155, y)
        y -= 15
        
        # Productos
        c.setFont("Helvetica", 8)
        total = 0
        
        for i in carrito:
            sub = i['cantidad'] * i['precio']
            total += sub
            
            # Acortar nombre si es muy largo
            prod_nom = i['nombre'][:18] + ".." if len(i['nombre']) > 18 else i['nombre']
            
            c.drawString(10, y, f"{i['cantidad']} x {prod_nom}")
            c.drawRightString(155, y, f"${sub:.2f}")
            y -= 12
            
            # Nueva página si se acaba el espacio
            if y < 50:
                c.showPage()
                y = 780
                c.setFont("Helvetica", 8)
        
        # Total
        y -= 5
        c.line(10, y, 155, y)
        y -= 15
        
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(155, y, f"TOTAL: ${total:.2f}")
        
        # Pie de página
        y -= 30
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(centro_x, y, "¡Gracias por su compra!")
        
        c.save()
        
        # Preguntar si abrir el ticket
        if messagebox.askyesno("Ticket Generado", "¿Abrir ticket de venta?"):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{path}"')
            else:  # linux
                os.system(f'xdg-open "{path}"')
    
    except Exception as e:
        print(f"Error al crear ticket: {e}")
        messagebox.showerror("Error", f"No se pudo crear el ticket: {e}")

def cargar_deudores():
    """Carga la lista de deudores de la sede actual"""
    global DEUDORES_CACHE
    try:
        if not sede_actual_id or not sede_actual_id.get():
            return
        
        tree_deu.delete(*tree_deu.get_children())
        data = api_get(f"/deudores/{sede_actual_id.get()}")
        
        DEUDORES_CACHE = {d['id']: d for d in data} if data else {}
        
        if data:
            for d in data:
                tree_deu.insert("", "end", iid=d['id'], 
                              values=(d.get('nombre', ''), 
                                     f"${d.get('deuda', 0):.2f}", 
                                     d.get('dia_visita', '')))
    
    except Exception as e:
        print(f"Error al cargar deudores: {e}")

def guardar_deudor():
    """Guarda un nuevo deudor"""
    try:
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showwarning("Advertencia", "Selecciona una sede primero")
            return
        
        nombre = entry_d_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Advertencia", "Ingresa el nombre del cliente")
            return
        
        try:
            deuda = float(entry_d_deuda.get() or 0)
            credito = float(entry_d_credito.get() or 0)
        except ValueError:
            messagebox.showerror("Error", "Deuda y crédito deben ser números válidos")
            return
        
        datos = {
            "sede_id": sede_actual_id.get(),
            "nombre": nombre,
            "deuda": deuda,
            "direccion": entry_d_dir.get().strip(),
            "telefono": entry_d_tel.get().strip(),
            "credito_autorizado": credito,
            "dia_visita": combo_d_dia.get()
        }
        
        if api_post("/deudores/agregar", datos):
            messagebox.showinfo("Éxito", "Cliente agregado correctamente")
            # Limpiar campos
            entry_d_nombre.delete(0, tk.END)
            entry_d_deuda.delete(0, tk.END)
            entry_d_dir.delete(0, tk.END)
            entry_d_tel.delete(0, tk.END)
            entry_d_credito.delete(0, tk.END)
            combo_d_dia.set("")
            cargar_deudores()
        else:
            messagebox.showerror("Error", "No se pudo agregar el cliente")
    
    except Exception as e:
        print(f"Error al guardar deudor: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def abonar():
    """Registra un abono a la deuda de un cliente"""
    try:
        sel = tree_deu.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Selecciona un cliente")
            return
        
        abono = simpledialog.askfloat("Abono", "Cantidad a abonar:", minvalue=0.01)
        if not abono:
            return
        
        if api_post("/deudores/abonar", {
            "id": int(sel[0]), 
            "abono": abono
        }):
            messagebox.showinfo("Éxito", f"Abono de ${abono:.2f} registrado")
            cargar_deudores()
        else:
            messagebox.showerror("Error", "No se pudo registrar el abono")
    
    except Exception as e:
        print(f"Error al abonar: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def ver_info_completa(event):
    """Muestra la información completa de un deudor al hacer clic derecho"""
    try:
        item = tree_deu.identify_row(event.y)
        if not item:
            return
        
        tree_deu.selection_set(item)
        did = int(item)
        
        if did in DEUDORES_CACHE:
            d = DEUDORES_CACHE[did]
            info = f"""
NOMBRE: {d.get('nombre', 'N/A')}
Dirección: {d.get('direccion', 'N/A')}
Teléfono: {d.get('telefono', 'N/A')}
Deuda: ${d.get('deuda', 0):.2f}
Crédito Autorizado: ${d.get('credito_autorizado', 0):.2f}
Día de Visita: {d.get('dia_visita', 'N/A')}
            """
            messagebox.showinfo("Información del Cliente", info.strip())
    
    except Exception as e:
        print(f"Error al ver info: {e}")

def cargar_reporte(e=None):
    """Carga el reporte de ventas según el filtro seleccionado"""
    try:
        if not sede_actual_id or not sede_actual_id.get():
            return
        
        filtro = cb_filtro.get()
        data = api_post("/ventas", {
            "sede_id": sede_actual_id.get(), 
            "filtro": filtro
        })
        
        tree_rep.delete(*tree_rep.get_children())
        fechas = []
        totales = []
        
        if data:
            for v in data:
                tree_rep.insert("", "end", 
                              values=(v.get('producto', ''), 
                                     v.get('cantidad', 0), 
                                     f"${v.get('total_venta', 0):.2f}", 
                                     v.get('fecha', '')))
                fechas.append(v.get('fecha', ''))
                totales.append(v.get('total_venta', 0))
            
            # Actualizar gráfica
            if fechas and totales:
                fig.clear()
                ax = fig.add_subplot(111)
                ax.plot(fechas, totales, marker='o')
                ax.set_xlabel('Fecha')
                ax.set_ylabel('Total Venta')
                ax.set_title('Evolución de Ventas')
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                fig.tight_layout()
                canvas_graf.draw()
    
    except Exception as e:
        print(f"Error al cargar reporte: {e}")
        messagebox.showerror("Error", f"Error al cargar reporte: {e}")

def corte_caja():
    """Realiza el corte de caja de la sede actual"""
    try:
        if not sede_actual_id or not sede_actual_id.get():
            messagebox.showwarning("Advertencia", "Selecciona una sede primero")
            return
        
        res = api_post(f"/corte_caja/{sede_actual_id.get()}", {})
        
        if res and "total_general" in res:
            imprimir_reporte_corte(res)
        else:
            mensaje = res.get("mensaje", "Error al realizar corte de caja") if res else "Error de conexión"
            messagebox.showinfo("Corte de Caja", mensaje)
    
    except Exception as e:
        print(f"Error en corte de caja: {e}")
        messagebox.showerror("Error", f"Error: {e}")

def imprimir_reporte_corte(data):
    """Genera el reporte PDF del corte de caja"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(CARPETA_REPORTES_CORTES, f"corte_{timestamp}.pdf")
        
        ancho_pag, alto_pag = letter
        c = canvas.Canvas(path, pagesize=letter)
        centro_x = ancho_pag / 2
        
        # Marca de agua con logo
        if os.path.exists(IMG_LOGO):
            try:
                c.saveState()
                c.drawImage(IMG_LOGO, x=(ancho_pag-450)/2, y=alto_pag/2 - 150, 
                          width=450, height=300, preserveAspectRatio=True, 
                          mask='auto', anchor='c')
                c.setFillAlpha(0.92)
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, ancho_pag, alto_pag, fill=1, stroke=0)
                c.restoreState()
            except:
                pass
        
        # Encabezado
        y = alto_pag - 60
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(centro_x, y, "DISTRIBUIDOR JORGE CHAVEZ")
        y -= 35
        
        c.setFont("Helvetica", 14)
        c.drawCentredString(centro_x, y, "Reporte de Corte de Caja")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawCentredString(centro_x, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 50
        
        # Cuadro de totales
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.rect(centro_x - 180, y - 120, 360, 120, fill=0)
        
        y_datos = y - 40
        x_labels = centro_x - 150
        x_values = centro_x + 150
        
        c.setFont("Helvetica", 12)
        
        # Total contado
        c.drawString(x_labels, y_datos, "Total Ventas Contado:")
        c.drawRightString(x_values, y_datos, f"${data.get('total_contado', 0):,.2f}")
        y_datos -= 30
        
        # Total crédito
        c.drawString(x_labels, y_datos, "Total Ventas Crédito:")
        c.drawRightString(x_values, y_datos, f"${data.get('total_credito', 0):,.2f}")
        y_datos -= 35
        
        # Línea separadora
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(x_labels, y_datos+5, x_values, y_datos+5)
        
        # Total general
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x_labels, y_datos-10, "TOTAL GENERAL:")
        c.drawRightString(x_values, y_datos-10, f"${data.get('total_general', 0):,.2f}")
        
        c.save()
        
        # Preguntar si abrir
        if messagebox.askyesno("Reporte Generado", "¿Abrir reporte de corte?"):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{path}"')
            else:  # linux
                os.system(f'xdg-open "{path}"')
    
    except Exception as e:
        print(f"Error al crear PDF de corte: {e}")
        messagebox.showerror("Error", f"No se pudo crear el reporte: {e}")

# --- GESTION USUARIOS Y SEDES ---
def abrir_gestion_usuarios():
    """Abre la ventana de gestión de usuarios y sedes"""
    try:
        win = tk.Toplevel(root)
        win.title("Gestión de Usuarios y Sedes")
        win.geometry("600x500")
        
        nb_gest = ttk.Notebook(win)
        nb_gest.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ========== PESTAÑA USUARIOS ==========
        f_users = tk.Frame(nb_gest)
        nb_gest.add(f_users, text="Usuarios")
        
        global USUARIOS_CACHE
        
        tk.Label(f_users, text="Usuarios Existentes:", font=("Arial", 10, "bold")).pack(pady=5)
        lb_u = tk.Listbox(f_users, width=50, height=10)
        lb_u.pack(pady=5, padx=10, fill="both", expand=True)
        
        def cargar_users():
            """Carga la lista de usuarios"""
            try:
                lb_u.delete(0, tk.END)
                global USUARIOS_CACHE
                data = api_get("/usuarios")
                USUARIOS_CACHE = data if data else []
                
                for u in USUARIOS_CACHE:
                    lb_u.insert(tk.END, f"{u.get('username', '')} ({u.get('rol', '')})")
            except Exception as e:
                print(f"Error al cargar usuarios: {e}")

        def eliminar_user():
            """Elimina un usuario seleccionado"""
            try:
                sel = lb_u.curselection()
                if not sel:
                    messagebox.showwarning("Advertencia", "Selecciona un usuario")
                    return
                
                uid = USUARIOS_CACHE[sel[0]]['id']
                username = USUARIOS_CACHE[sel[0]]['username']
                
                if messagebox.askyesno("Confirmar", f"¿Eliminar usuario '{username}'?"):
                    requests.delete(f"{API_URL}/usuarios/eliminar/{uid}", timeout=10)
                    messagebox.showinfo("Éxito", "Usuario eliminado")
                    cargar_users()
            except Exception as e:
                print(f"Error al eliminar usuario: {e}")
                messagebox.showerror("Error", f"Error: {e}")

        cargar_users()
        
        tk.Button(f_users, text="ELIMINAR SELECCIONADO", bg="red", fg="white", 
                 command=eliminar_user).pack(pady=5)
        
        # Formulario nuevo usuario
        f_add = tk.LabelFrame(f_users, text="Agregar Nuevo Usuario", padx=10, pady=10)
        f_add.pack(fill="x", pady=10, padx=10)
        
        tk.Label(f_add, text="Usuario:").pack(side="left", padx=5)
        e_u = tk.Entry(f_add, width=15)
        e_u.pack(side="left", padx=5)
        
        tk.Label(f_add, text="Contraseña:").pack(side="left", padx=5)
        e_p = tk.Entry(f_add, width=15, show="*")
        e_p.pack(side="left", padx=5)
        
        cb_rol = ttk.Combobox(f_add, values=["vendedor", "admin"], width=10, state="readonly")
        cb_rol.set("vendedor")
        cb_rol.pack(side="left", padx=5)
        
        def agregar_u():
            """Agrega un nuevo usuario"""
            try:
                username = e_u.get().strip()
                password = e_p.get().strip()
                rol = cb_rol.get()
                
                if not username or not password:
                    messagebox.showwarning("Advertencia", "Completa todos los campos")
                    return
                
                if api_post("/usuarios/agregar", {
                    "username": username,
                    "password": password,
                    "rol": rol
                }):
                    messagebox.showinfo("Éxito", "Usuario creado correctamente")
                    e_u.delete(0, tk.END)
                    e_p.delete(0, tk.END)
                    cb_rol.set("vendedor")
                    cargar_users()
                else:
                    messagebox.showerror("Error", "No se pudo crear el usuario")
            except Exception as e:
                print(f"Error al agregar usuario: {e}")
                messagebox.showerror("Error", f"Error: {e}")
        
        tk.Button(f_add, text="Crear Usuario", command=agregar_u, bg="lime").pack(side="left", padx=5)

        # ========== PESTAÑA SEDES ==========
        f_sedes = tk.Frame(nb_gest)
        nb_gest.add(f_sedes, text="Sedes")
        
        tk.Label(f_sedes, text="Sedes Existentes:", font=("Arial", 10, "bold")).pack(pady=5)
        lb_s = tk.Listbox(f_sedes, width=50, height=10)
        lb_s.pack(pady=5, padx=10, fill="both", expand=True)

        def cargar_sedes_list():
            """Carga la lista de sedes"""
            try:
                lb_s.delete(0, tk.END)
                global SEDES_CACHE
                data = api_get("/sedes")
                SEDES_CACHE = data if data else []
                
                for s in SEDES_CACHE:
                    lb_s.insert(tk.END, f"{s.get('nombre', '')} (ID: {s.get('id', '')})")
            except Exception as e:
                print(f"Error al cargar sedes: {e}")

        def eliminar_sede():
            """Elimina una sede (PELIGRO: borra todo el inventario)"""
            try:
                sel = lb_s.curselection()
                if not sel:
                    messagebox.showwarning("Advertencia", "Selecciona una sede")
                    return
                
                sid = SEDES_CACHE[sel[0]]['id']
                nombre_sede = SEDES_CACHE[sel[0]]['nombre']
                
                if messagebox.askyesno("⚠️ PELIGRO ⚠️", 
                    f"Si borras la sede '{nombre_sede}', SE BORRARÁ TODO SU INVENTARIO.\n\n¿Estás COMPLETAMENTE seguro?"):
                    requests.delete(f"{API_URL}/sedes/eliminar/{sid}", timeout=10)
                    messagebox.showinfo("Éxito", "Sede eliminada")
                    cargar_sedes_list()
                    cargar_sedes_gui()
            except Exception as e:
                print(f"Error al eliminar sede: {e}")
                messagebox.showerror("Error", f"Error: {e}")

        cargar_sedes_list()
        
        tk.Button(f_sedes, text="⚠️ ELIMINAR SEDE (PELIGRO) ⚠️", bg="red", fg="white", 
                 command=eliminar_sede).pack(pady=5)
        
        # Formulario nueva sede
        f_adds = tk.LabelFrame(f_sedes, text="Agregar Nueva Sede", padx=10, pady=10)
        f_adds.pack(fill="x", pady=10, padx=10)
        
        tk.Label(f_adds, text="Nombre de la sede:").pack(side="left", padx=5)
        e_s = tk.Entry(f_adds, width=30)
        e_s.pack(side="left", padx=5)
        
        def crear_sede():
            """Crea una nueva sede"""
            try:
                nombre = e_s.get().strip()
                if not nombre:
                    messagebox.showwarning("Advertencia", "Ingresa el nombre de la sede")
                    return
                
                if api_post("/sedes/agregar", {"nombre": nombre}):
                    messagebox.showinfo("Éxito", "Sede creada correctamente")
                    e_s.delete(0, tk.END)
                    cargar_sedes_list()
                    cargar_sedes_gui()
                else:
                    messagebox.showerror("Error", "No se pudo crear la sede")
            except Exception as e:
                print(f"Error al crear sede: {e}")
                messagebox.showerror("Error", f"Error: {e}")
        
        tk.Button(f_adds, text="Crear Sede", command=crear_sede, bg="lime").pack(side="left", padx=5)
    
    except Exception as e:
        print(f"Error al abrir gestión: {e}")
        messagebox.showerror("Error", f"Error: {e}")

# --- FUNCION PRINCIPAL GUI ---
def iniciar_aplicacion_principal(rol_usuario, nombre_usuario_login):
    """Inicia la aplicación principal con la interfaz gráfica"""
    global root, alerta_stock_var, alerta_dias_var, modo_super, sede_actual_id, sede_actual_nombre
    global ROL_ACTUAL, usuario_actual_nombre
    global entry_codigo, entry_id, entry_nombre, entry_cant, entry_precio, tree_inv
    global tree_inv_venta, tree_cart, lbl_total, e_scan_venta
    global entry_d_nombre, entry_d_deuda, entry_d_dir, entry_d_tel, entry_d_credito, combo_d_dia, tree_deu
    global cb_filtro, tree_rep, canvas_graf, cb_sedes, entry_buscar_inventario, fig, tree_sol
    global background_image_tk

    try:
        ROL_ACTUAL = rol_usuario
        usuario_actual_nombre = nombre_usuario_login
        
        root = tk.Tk()
        root.geometry(RESOLUCION_INICIAL)
        root.title(f"Jorge Chavez Distribuidor ({ROL_ACTUAL.upper()}: {usuario_actual_nombre})")
        
        # Cargar imagen de fondo
        try:
            if os.path.exists(IMG_FONDO):
                pil_img = Image.open(IMG_FONDO)
                pil_img = pil_img.resize((1366, 768), Image.LANCZOS)
                blurred_img = pil_img.filter(ImageFilter.GaussianBlur(radius=30))
                background_image_tk = ImageTk.PhotoImage(blurred_img)
                bg_label = tk.Label(root, image=background_image_tk)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                bg_label.lower()
        except Exception as e:
            print(f"No se pudo cargar imagen de fondo: {e}")

        # Variables de control
        sede_actual_id = tk.IntVar()
        sede_actual_nombre = tk.StringVar()
        alerta_stock_var = tk.IntVar(value=ALERTA_STOCK_INICIAL)
        alerta_dias_var = tk.IntVar(value=ALERTA_DIAS_CREDITO_INICIAL)
        modo_super = tk.BooleanVar()

        # Frame superior
        f_top = tk.Frame(root, bg="#333")
        f_top.pack(fill="x")
        tk.Label(f_top, text="SEDE:", fg="white", bg="#333", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        cb_sedes = ttk.Combobox(f_top, textvariable=sede_actual_nombre, state="readonly", width=30)
        cb_sedes.pack(side="left", padx=5)
        cb_sedes.bind("<<ComboboxSelected>>", cambiar_sede)

        # Notebook principal
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=5, pady=5)

        # ========== 1. PESTAÑA INVENTARIO ==========
        p_inv = tk.Frame(nb)
        nb.add(p_inv, text="📦 Inventario")
        
        # Búsqueda
        f_bus = tk.Frame(p_inv)
        f_bus.pack(fill="x", padx=10, pady=5)
        tk.Label(f_bus, text="🔍 Buscar:").pack(side="left", padx=5)
        entry_buscar_inventario = tk.Entry(f_bus)
        entry_buscar_inventario.pack(side="left", fill="x", expand=True, padx=5)
        entry_buscar_inventario.bind("<Return>", buscar_producto)
        tk.Button(f_bus, text="Buscar", command=buscar_producto, bg="lightblue").pack(side="left", padx=5)
        tk.Button(f_bus, text="📂 CATÁLOGO", bg="#FFD700", command=abrir_catalogo_maestro).pack(side="right", padx=10)
        
        # Formulario
        f_form = tk.LabelFrame(p_inv, text="Datos del Producto", padx=10, pady=10)
        f_form.pack(pady=5, padx=10, fill="x")
        
        tk.Checkbutton(f_form, text="⚡ Modo Supermercado (Escanea = +1)", 
                      variable=modo_super, font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        tk.Label(f_form, text="Código de Barras:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        entry_codigo = tk.Entry(f_form, width=30)
        entry_codigo.grid(row=1, column=1, padx=5, pady=2)
        entry_codigo.bind("<Return>", scan_codigo_inv)
        
        tk.Label(f_form, text="ID Producto:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        entry_id = tk.Entry(f_form, width=30)
        entry_id.grid(row=2, column=1, padx=5, pady=2)
        
        tk.Label(f_form, text="Nombre:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        entry_nombre = tk.Entry(f_form, width=30)
        entry_nombre.grid(row=3, column=1, padx=5, pady=2)
        
        tk.Label(f_form, text="Cantidad:").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        entry_cant = tk.Entry(f_form, width=30)
        entry_cant.grid(row=4, column=1, padx=5, pady=2)
        
        tk.Label(f_form, text="Precio:").grid(row=5, column=0, sticky="e", padx=5, pady=2)
        entry_precio = tk.Entry(f_form, width=30)
        entry_precio.grid(row=5, column=1, padx=5, pady=2)
        
        # Botones
        f_btn = tk.Frame(p_inv)
        f_btn.pack(pady=10)
        
        tk.Button(f_btn, text="➕ Agregar Nuevo", bg="#90EE90", command=agregar_producto).pack(side="left", padx=5)
        tk.Button(f_btn, text="✏️ Cargar Datos", command=editar_producto).pack(side="left", padx=5)
        tk.Button(f_btn, text="💾 ACTUALIZAR", bg="#4169E1", fg="white", 
                 command=actualizar_producto_inv).pack(side="left", padx=5)
        tk.Button(f_btn, text="🧹 Limpiar", command=limpiar_form_inv).pack(side="left", padx=5)
        
        # Botones de admin
        st_btn = "normal" if ROL_ACTUAL == 'admin' else "disabled"
        tk.Button(f_btn, text="🗑️ Eliminar", command=eliminar_producto, 
                 state=st_btn, bg="salmon").pack(side="left", padx=5)
        tk.Button(f_btn, text="📦 Transferir", bg="gold", command=transferir_stock, 
                 state=st_btn).pack(side="left", padx=5)
        
        # TreeView inventario
        frame_tree_inv = tk.Frame(p_inv)
        frame_tree_inv.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar_inv = ttk.Scrollbar(frame_tree_inv)
        scrollbar_inv.pack(side="right", fill="y")
        
        tree_inv = ttk.Treeview(frame_tree_inv, columns=("c", "i", "n", "s", "p"), 
                               show="headings", yscrollcommand=scrollbar_inv.set)
        tree_inv.pack(fill="both", expand=True)
        scrollbar_inv.config(command=tree_inv.yview)
        
        for c, h, w in zip(["c", "i", "n", "s", "p"], 
                          ["Código", "ID", "Nombre", "Stock", "Precio"],
                          [120, 100, 300, 80, 100]):
            tree_inv.heading(c, text=h)
            tree_inv.column(c, width=w)
        
        tree_inv.tag_configure('bajo', background='#FFB6C1')

        # ========== 2. PUNTO DE VENTA ==========
        p_pos = tk.Frame(nb)
        nb.add(p_pos, text="💰 Punto de Venta")
        
        # Scanner
        f_scan = tk.LabelFrame(p_pos, text="🔍 Escanear Código de Barras", pady=5)
        f_scan.pack(fill="x", padx=10, pady=5)
        e_scan_venta = tk.Entry(f_scan, font=("Arial", 12))
        e_scan_venta.pack(fill="x", padx=10)
        e_scan_venta.bind("<Return>", scan_venta)
        
        # Panel dividido
        paned = tk.PanedWindow(p_pos, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Inventario disponible
        f_izq = tk.LabelFrame(paned, text="Productos Disponibles")
        paned.add(f_izq)
        
        tree_inv_venta = ttk.Treeview(f_izq, columns=("id", "nom", "st", "pr"), show="headings")
        tree_inv_venta.pack(fill="both", expand=True)
        tree_inv_venta.bind("<Double-1>", lambda e: anadir_manual_venta())
        
        for c, h in zip(["id", "nom", "st", "pr"], 
                       ["ID", "Nombre", "Stock", "Precio"]):
            tree_inv_venta.heading(c, text=h)
        
        tk.Button(f_izq, text="➕ Añadir al Carrito", command=anadir_manual_venta, 
                 bg="lightblue").pack(fill="x", padx=5, pady=5)
        
        # Carrito
        f_der = tk.LabelFrame(paned, text="🛒 Carrito de Compra")
        paned.add(f_der)
        
        tree_cart = ttk.Treeview(f_der, columns=("n", "c", "p", "s"), show="headings")
        tree_cart.pack(fill="both", expand=True)
        
        for c, h in zip(["n", "c", "p", "s"], 
                       ["Producto", "Cant", "Precio", "Subtotal"]):
            tree_cart.heading(c, text=h)
        
        lbl_total = tk.Label(f_der, text="Total: $0.00", font=("Arial", 16, "bold"), fg="darkgreen")
        lbl_total.pack(pady=5)
        
        tk.Button(f_der, text="➖ Quitar del Carrito", command=quitar_carrito, 
                 bg="salmon").pack(fill="x", padx=5, pady=2)
        tk.Button(f_der, text="✅ FINALIZAR VENTA", bg="lime", font=("Arial", 12, "bold"), 
                 command=finalizar_venta).pack(fill="x", padx=5, pady=5)

        # ========== 3. DEUDORES ==========
        p_deu = tk.Frame(nb)
        nb.add(p_deu, text="💳 Clientes/Deudores")
        
        # Formulario
        f_d_form = tk.LabelFrame(p_deu, text="Agregar/Editar Cliente", padx=10, pady=10)
        f_d_form.pack(fill="x", padx=10, pady=5)
        
        tk.Label(f_d_form, text="Nombre:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        entry_d_nombre = tk.Entry(f_d_form, width=20)
        entry_d_nombre.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(f_d_form, text="Deuda Inicial $:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
        entry_d_deuda = tk.Entry(f_d_form, width=15)
        entry_d_deuda.grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(f_d_form, text="Dirección:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        entry_d_dir = tk.Entry(f_d_form, width=20)
        entry_d_dir.grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(f_d_form, text="Teléfono:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        entry_d_tel = tk.Entry(f_d_form, width=15)
        entry_d_tel.grid(row=1, column=3, padx=5, pady=2)
        
        tk.Label(f_d_form, text="Crédito Máximo $:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        entry_d_credito = tk.Entry(f_d_form, width=20)
        entry_d_credito.grid(row=2, column=1, padx=5, pady=2)
        
        tk.Label(f_d_form, text="Día de Visita:").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        combo_d_dia = ttk.Combobox(f_d_form, 
                                   values=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
                                   state="readonly", width=13)
        combo_d_dia.grid(row=2, column=3, padx=5, pady=2)
        
        tk.Button(f_d_form, text="💾 Guardar Cliente", bg="#90EE90", 
                 command=guardar_deudor).grid(row=3, column=0, columnspan=4, pady=10)
        
        # TreeView deudores
        frame_tree_deu = tk.Frame(p_deu)
        frame_tree_deu.pack(fill="both", expand=True, padx=10, pady=5)
        
        tree_deu = ttk.Treeview(frame_tree_deu, columns=("n", "d", "v"), show="headings")
        tree_deu.pack(fill="both", expand=True)
        tree_deu.bind("<Button-3>", ver_info_completa)  # Clic derecho
        
        for c, h in zip(["n", "d", "v"], 
                       ["Nombre del Cliente", "Deuda Actual", "Día de Visita"]):
            tree_deu.heading(c, text=h)
        
        tk.Label(p_deu, text="💡 Clic derecho en un cliente para ver información completa", 
                fg="gray", font=("Arial", 9, "italic")).pack()
        
        tk.Button(p_deu, text="💵 ABONAR A DEUDA", bg="gold", font=("Arial", 11, "bold"), 
                 command=abonar).pack(fill="x", padx=10, pady=5)

        # ========== 4. REPORTES ==========
        p_rep = tk.Frame(nb)
        nb.add(p_rep, text="📊 Reportes")
        
        # Filtros
        f_rep_top = tk.Frame(p_rep)
        f_rep_top.pack(fill="x", padx=10, pady=5)
        
        tk.Label(f_rep_top, text="Filtro:").pack(side="left", padx=5)
        cb_filtro = ttk.Combobox(f_rep_top, 
                                values=["Mostrar Todo", "Última hora", "Último día"], 
                                state="readonly")
        cb_filtro.set("Mostrar Todo")
        cb_filtro.pack(side="left", padx=5)
        cb_filtro.bind("<<ComboboxSelected>>", cargar_reporte)
        
        tk.Button(f_rep_top, text="🔄 Actualizar", command=cargar_reporte, 
                 bg="lightblue").pack(side="left", padx=5)
        tk.Button(f_rep_top, text="💰 CORTE DE CAJA", bg="red", fg="white", 
                 font=("Arial", 10, "bold"), command=corte_caja).pack(side="right", padx=10)
        
        # TreeView reportes
        tree_rep = ttk.Treeview(p_rep, columns=("p", "c", "t", "f"), show="headings", height=8)
        tree_rep.pack(fill="x", padx=10, pady=5)
        
        for c, h in zip(["p", "c", "t", "f"], 
                       ["Producto", "Cantidad", "Total", "Fecha"]):
            tree_rep.heading(c, text=h)
        
        # Gráfica
        fig = plt.Figure(figsize=(5, 3), dpi=100)
        canvas_graf = FigureCanvasTkAgg(fig, master=p_rep)
        canvas_graf.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        # ========== 5. SOLICITUDES (SOLO ADMIN) ==========
        if ROL_ACTUAL == 'admin':
            p_sol = tk.Frame(nb)
            nb.add(p_sol, text="📋 Solicitudes de Stock")
            
            tk.Label(p_sol, text="Solicitudes Pendientes de Aprobación", 
                    font=("Arial", 12, "bold")).pack(pady=5)
            
            tk.Button(p_sol, text="🔄 Refrescar Lista", command=lambda: cargar_solicitudes_pendientes(tree_sol), 
                     bg="lightblue").pack(pady=5)
            
            tree_sol = ttk.Treeview(p_sol, columns=("fecha", "sede", "user", "prod", "cant"), 
                                   show="headings")
            tree_sol.pack(fill="both", expand=True, padx=10, pady=5)
            
            for c, h in zip(["fecha", "sede", "user", "prod", "cant"], 
                           ["Fecha", "Sede", "Usuario", "Producto", "Cantidad"]):
                tree_sol.heading(c, text=h)
            
            f_sol_btn = tk.Frame(p_sol)
            f_sol_btn.pack(pady=10)
            
            tk.Button(f_sol_btn, text="✅ APROBAR", bg="lime", font=("Arial", 11, "bold"), 
                     command=lambda: aprobar_solicitud(tree_sol)).pack(side="left", padx=10)
            tk.Button(f_sol_btn, text="❌ RECHAZAR", bg="red", fg="white", font=("Arial", 11, "bold"), 
                     command=lambda: rechazar_solicitud(tree_sol)).pack(side="left", padx=10)
            
            cargar_solicitudes_pendientes(tree_sol)

        # ========== 6. CONFIGURACIÓN (SOLO ADMIN) ==========
        if ROL_ACTUAL == 'admin':
            p_conf = tk.Frame(nb)
            nb.add(p_conf, text="⚙️ Configuración")
            
            tk.Label(p_conf, text="Panel de Administración", 
                    font=("Arial", 14, "bold")).pack(pady=20)
            
            tk.Button(p_conf, text="👥 GESTIONAR USUARIOS Y SEDES", 
                     bg="orange", font=("Arial", 12, "bold"), 
                     command=abrir_gestion_usuarios).pack(pady=10, ipadx=20, ipady=10)
            
            tk.Label(p_conf, text="\n⚠️ Advertencia: La gestión de usuarios y sedes requiere permisos de administrador", 
                    fg="red", font=("Arial", 9, "italic")).pack()

        # Cerrar aplicación
        def cerrar_app():
            """Cierra la aplicación guardando la configuración"""
            try:
                guardar_configuracion()
                root.destroy()
            except Exception as e:
                print(f"Error al cerrar: {e}")
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", cerrar_app)
        
        # Cargar datos iniciales
        root.after(500, cargar_sedes_gui)
        
        root.mainloop()
    
    except Exception as e:
        print(f"Error crítico al iniciar aplicación: {e}")
        messagebox.showerror("Error Fatal", f"No se pudo iniciar la aplicación:\n{e}")
        if root:
            root.destroy()

# --- LOGIN ---
def login_screen():
    """Pantalla de inicio de sesión"""
    try:
        login_win = tk.Tk()
        login_win.title("Iniciar Sesión - Jorge Chavez Distribuidor")
        login_win.geometry("400x300")
        login_win.resizable(False, False)
        
        # Centrar ventana
        login_win.update_idletasks()
        width = login_win.winfo_width()
        height = login_win.winfo_height()
        x = (login_win.winfo_screenwidth() // 2) - (width // 2)
        y = (login_win.winfo_screenheight() // 2) - (height // 2)
        login_win.geometry(f'{width}x{height}+{x}+{y}')
        
        # Frame principal
        main_frame = tk.Frame(login_win, bg="white")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        tk.Label(main_frame, text="JORGE CHAVEZ", 
                font=("Arial", 18, "bold"), bg="white").pack(pady=10)
        tk.Label(main_frame, text="Sistema de Ventas", 
                font=("Arial", 10), bg="white", fg="gray").pack()
        
        # Separador
        tk.Frame(main_frame, height=2, bg="lightgray").pack(fill="x", pady=20)
        
        # Campos
        tk.Label(main_frame, text="Usuario:", bg="white", 
                font=("Arial", 10)).pack(anchor="w", padx=20)
        e_user = tk.Entry(main_frame, font=("Arial", 11), width=25)
        e_user.pack(pady=5, padx=20)
        
        tk.Label(main_frame, text="Contraseña:", bg="white", 
                font=("Arial", 10)).pack(anchor="w", padx=20, pady=(10, 0))
        e_pass = tk.Entry(main_frame, show="●", font=("Arial", 11), width=25)
        e_pass.pack(pady=5, padx=20)
        
        def try_login():
            """Intenta iniciar sesión"""
            try:
                u = e_user.get().strip()
                p = e_pass.get().strip()
                
                if not u or not p:
                    messagebox.showwarning("Advertencia", "Completa todos los campos")
                    return
                
                # Mostrar mensaje de espera
                btn_login.config(text="Conectando...", state="disabled")
                login_win.update()
                
                res = api_post("/login", {"username": u, "password": p})
                
                if res and "mensaje" in res and res["mensaje"] == "Login exitoso":
                    rol = res.get("rol", "vendedor")
                    login_win.destroy()
                    iniciar_aplicacion_principal(rol, u)
                else:
                    btn_login.config(text="INICIAR SESIÓN", state="normal")
                    messagebox.showerror("Error", "Usuario o contraseña incorrectos")
                    e_pass.delete(0, tk.END)
            
            except Exception as e:
                btn_login.config(text="INICIAR SESIÓN", state="normal")
                print(f"Error en login: {e}")
                messagebox.showerror("Error de Conexión", 
                                   f"No se pudo conectar al servidor:\n{e}")
        
        # Botón login
        btn_login = tk.Button(main_frame, text="INICIAR SESIÓN", 
                             command=try_login, bg="#4CAF50", fg="white", 
                             font=("Arial", 11, "bold"), cursor="hand2")
        btn_login.pack(pady=20, ipadx=20, ipady=5)
        
        # Enter para login
        e_pass.bind("<Return>", lambda e: try_login())
        e_user.bind("<Return>", lambda e: e_pass.focus())
        
        # Foco inicial
        e_user.focus()
        
        login_win.mainloop()
    
    except Exception as e:
        print(f"Error en pantalla de login: {e}")
        messagebox.showerror("Error Fatal", f"No se pudo iniciar la aplicación:\n{e}")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    try:
        # Cargar configuración al inicio
        cargar_configuracion()
        
        # Iniciar pantalla de login
        login_screen()
    
    except Exception as e:
        print(f"Error fatal al iniciar: {e}")
        messagebox.showerror("Error Fatal", f"Error crítico:\n{e}")
