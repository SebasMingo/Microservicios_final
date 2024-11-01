from flask import Flask, request, jsonify
import sqlite3
import os
from flask_cors import CORS
import pika
import json
import jwt
import datetime
import pybreaker

SECRET_KEY = "1234"

app = Flask(__name__)
CORS(app)

breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)

def generar_token_microservicio():
    payload = {
        "servicio": "pedidos",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=5)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

@breaker
def enviar_mensaje(producto_id, cantidad):
    try:
        conexion = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        canal = conexion.channel()
        canal.queue_declare(queue='pedidos_queue')

        token = generar_token_microservicio()

        mensaje = {
            'producto_id': producto_id,
            'cantidad': cantidad,
            'token': token
        }

        canal.basic_publish(exchange='', routing_key='pedidos_queue', body=json.dumps(mensaje))
        print(f"Pedido enviado: {mensaje}")

        conexion.close()
    except Exception as e:
        print("Error al enviar mensaje a RabbitMQ:", e)
        raise

def connect_db():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'db', 'pedidos.db')
    conn = sqlite3.connect(db_path)
    return conn

def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            cantidad INTEGER
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/pedidos', methods=['POST'])
def crear_pedido():
    nuevo_pedido = request.json
    producto_id = nuevo_pedido['producto_id']
    cantidad = nuevo_pedido['cantidad']
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pedidos (producto_id, cantidad) VALUES (?, ?)", (producto_id, cantidad))
    conn.commit()
    conn.close()
    
    try:
        enviar_mensaje(producto_id, cantidad)
        return jsonify({'message': 'Pedido creado exitosamente'}), 201
    except pybreaker.CircuitBreakerError:
        return jsonify({'error': 'Servicio de inventario no disponible, intenta más tarde'}), 503

@app.route('/pedidos', methods=['GET'])
def obtener_pedidos():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos")
    pedidos = cursor.fetchall()
    conn.close()
    return jsonify(pedidos)

if __name__ == '__main__':
    create_table()
    app.run(port=10000, debug=True)
