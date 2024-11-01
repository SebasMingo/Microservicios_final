from flask import Flask, request, jsonify
import sqlite3
import os
from flask_cors import CORS
import pika
import json
import jwt
import time
from threading import Thread

app = Flask(__name__)
CORS(app)

SECRET_KEY = "1234"

def connect_db():
    base_dir = os.getcwd()
    db_path = os.path.join(base_dir, 'db', 'productos.db')

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        create_table()
    else:
        conn = sqlite3.connect(db_path)

    return conn

# Crear tabla de productos si no existe
def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            precio REAL,
            stock INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Función para actualizar el inventario
def actualizar_inventario(producto_id, cantidad):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, producto_id))
    conn.commit()
    conn.close()

# Callback para procesar mensajes de RabbitMQ y verificar el token
def callback(ch, method, properties, body):
    mensaje = json.loads(body)
    token = mensaje.get('token')

    if not token:
        print("Token no encontrado en el mensaje")
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("servicio") != "pedidos":
            print("Acceso denegado: servicio no autorizado")
            return
    except jwt.ExpiredSignatureError:
        print("Token expirado")
        return
    except jwt.InvalidTokenError:
        print("Token inválido")
        return

    producto_id = mensaje['producto_id']
    cantidad = mensaje['cantidad']
    actualizar_inventario(producto_id, cantidad)
    print(f"Inventario actualizado: Producto {producto_id}, Cantidad reducida {cantidad}")

# Consumir mensajes de RabbitMQ con reintentos
def consumir_mensajes():
    intentos = 5
    espera_reintento = 5

    while intentos > 0:
        try:
            conexion = pika.BlockingConnection(
                pika.ConnectionParameters(host='localhost', heartbeat=600, blocked_connection_timeout=300)
            )
            canal = conexion.channel()
            canal.queue_declare(queue='pedidos_queue')
            canal.basic_consume(queue='pedidos_queue', on_message_callback=callback, auto_ack=True)

            print('Esperando mensajes para actualizar inventario...')
            canal.start_consuming()
            break

        except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelError) as e:
            print(f"Error al conectar con RabbitMQ: {e}")
            intentos -= 1
            print(f"Reintentando en {espera_reintento} segundos...")
            time.sleep(espera_reintento)
            
    if intentos == 0:
        print("No se pudo conectar a RabbitMQ después de múltiples intentos.")

# Endpoint para obtener todos los productos
@app.route('/productos', methods=['GET'])
def obtener_productos():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conn.close()
    return jsonify(productos)

# Endpoint para crear un nuevo producto
@app.route('/productos', methods=['POST'])
def crear_producto():
    nuevo_producto = request.json
    nombre = nuevo_producto['nombre']
    precio = nuevo_producto['precio']
    stock = nuevo_producto.get('stock', 0)
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)", (nombre, precio, stock))
    producto_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Producto creado exitosamente', 'producto_id': producto_id}), 201

if __name__ == '__main__':
    create_table()
    thread = Thread(target=consumir_mensajes)
    thread.start()
    app.run(port=10001, debug=True)
