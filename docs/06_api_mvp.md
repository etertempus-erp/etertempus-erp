# API MVP

## Organizacion inicial

El seed crea Eter Tempus con este identificador:

```text
00000000-0000-0000-0000-000000000001
```

## Flujo manual de prueba

### 1. Consultar recursos

```http
GET /resources?organization_id=00000000-0000-0000-0000-000000000001
```

### 2. Consultar stock

```http
GET /resources/stock?organization_id=00000000-0000-0000-0000-000000000001
```

### 3. Crear recurso

```http
POST /resources
Content-Type: application/json

{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "code": "MP-0005",
  "name": "Lavanda",
  "type": "raw_material",
  "unit": "g",
  "minimum_stock": 25
}
```

### 4. Cargar stock inicial

```http
POST /resources/{resource_id}/stock-adjustments
Content-Type: application/json

{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "quantity": 100,
  "unit": "g",
  "reason": "Carga inicial de stock"
}
```

### 5. Escalar formula

```http
POST /formulas/{formula_id}/scale
Content-Type: application/json

{
  "target_weight": 400
}
```

### 6. Crear lote

```http
POST /production/batches
Content-Type: application/json

{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "product_resource_id": "{id del producto Rosa del Alba}",
  "formula_id": "{id de la formula Rosa del Alba v1}",
  "elaboration_date": "2026-07-27",
  "target_weight": 400,
  "notes": "Primer lote de prueba"
}
```

## Resultado esperado

Al crear el lote:

- Se crea un recurso tipo `mix`.
- Se descuenta materia prima.
- Se suma stock de mezcla.
- Se generan movimientos trazables.
- El lote queda vinculado a la version exacta de la formula.

### 7. Consultar opciones de venta

```http
GET /sales/options?organization_id=00000000-0000-0000-0000-000000000001
```

Devuelve canales, medios de pago y puntos de venta.

### 8. Consultar productos disponibles para vender

```http
GET /sales/products/available-for-sale?organization_id=00000000-0000-0000-0000-000000000001
```

Devuelve productos activos, stock calculado y precio sugerido cuando existe.

### 9. Crear venta

```http
POST /sales
Content-Type: application/json

{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "sale_date": "2026-07-27",
  "channel_id": "{id del canal}",
  "point_of_sale_id": null,
  "customer_name": "Cliente opcional",
  "payment_method_id": "{id del medio de pago}",
  "notes": "Venta de prueba",
  "lines": [
    {
      "product_resource_id": "{id del producto}",
      "quantity": 1,
      "unit_price": 300,
      "discount": 0
    }
  ]
}
```

Resultado esperado:

- Se crea una venta confirmada.
- Se genera codigo automatico `V-AAAA-0001`.
- Se descuenta stock con movimiento `sale`.
- Si falta stock, la venta completa se rechaza.

### 10. Historial de ventas

```http
GET /sales?organization_id=00000000-0000-0000-0000-000000000001
```

Filtros disponibles:

- `date_from`
- `date_to`
- `channel_id`
- `point_of_sale_id`
- `product_resource_id`
- `payment_method_id`
- `status`

El historial muestra ventas del sistema y ventas importadas. Las importadas aparecen con `source = imported` y no tienen movimientos de inventario.

### 11. Anular venta

```http
POST /sales/{sale_id}/cancel
Content-Type: application/json

{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "reason": "Error de carga"
}
```

Resultado esperado:

- La venta queda en estado `cancelled`.
- Se generan movimientos `sale_cancellation`.
- El stock vuelve al recurso vendido.

### 12. Crear compra en borrador

```http
POST /purchases
Content-Type: application/json

{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "purchase_date": "2026-07-27",
  "supplier_name": "Niter",
  "receipt_number": "A-001",
  "notes": "Compra de materias primas",
  "lines": [
    {
      "resource_id": "{id del recurso}",
      "quantity": 500,
      "unit": "g",
      "unit_price": 1.25
    }
  ]
}
```

Resultado esperado:

- Se crea una compra en estado `draft`.
- No se modifica stock.

### 13. Confirmar compra

```http
POST /purchases/{purchase_id}/confirm?organization_id=00000000-0000-0000-0000-000000000001
```

Resultado esperado:

- La compra pasa a `confirmed`.
- Se generan movimientos `purchase`.
- Aumenta el stock de cada recurso comprado.
- Se guarda el costo unitario de compra.
