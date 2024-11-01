# API Contrato de Microservicios

Este documento describe el contrato de la API para los microservicios de **Pedidos** y **Productos** en el sistema.

---

## Autenticación

Algunos endpoints requieren autenticación mediante un token JWT. Este token debe incluirse en el encabezado `Authorization` como `Bearer <token>`.

---

## Microservicio de Pedidos

### Endpoint: Crear Pedido
- **URL**: `/pedidos`
- **Método**: `POST`
- **Descripción**: Crea un nuevo pedido y envía una solicitud para actualizar el inventario en el microservicio de **Productos**.
  
#### Parámetros de Entrada
- **Body** (JSON):
  - `producto_id` (int): ID del producto a pedir.
  - `cantidad` (int): Cantidad del producto.

#### Ejemplo de Solicitud

POST /pedidos
```json
{
    "producto_id": 1,
    "cantidad": 5
}
```

### Endpoint: Obtener Pedidos
- **URL**: `/pedidos`
- **Método**: `GET`
- **Descripción**: Devuelve una lista de todos los pedidos.

#### Respuesta Exitosa
- **Código**: `200 OK`
- **Body (JSON)**:
```json
[
    {
        "id": 1,
        "producto_id": 1,
        "cantidad": 5
    },
    {
        "id": 2,
        "producto_id": 2,
        "cantidad": 3
    }
]