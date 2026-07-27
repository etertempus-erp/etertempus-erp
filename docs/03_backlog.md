# Backlog Inicial

## Epic 1 - Recursos

### US-001 Crear recurso

Como usuaria, quiero registrar una materia prima, packaging o producto para que pueda participar en compras, formulas, produccion e inventario.

Criterios de aceptacion:

- Permite nombre, codigo, tipo y unidad.
- No permite codigos duplicados.
- Permite desactivar sin borrar.
- El recurso queda disponible para movimientos.

### US-002 Consultar recursos

Como usuaria, quiero ver y filtrar recursos para encontrar rapidamente materias primas, packaging y productos.

Criterios de aceptacion:

- Permite filtrar por tipo.
- Permite buscar por nombre o codigo.
- Muestra si el recurso esta activo.

## Epic 2 - Formulas

### US-003 Crear formula versionada

Como Tea Blender, quiero crear una formula en porcentaje para poder escalarla a cualquier peso de produccion.

Criterios de aceptacion:

- La suma de porcentajes debe ser 100.
- Cada ingrediente debe ser un recurso activo.
- La formula pertenece a un producto o puede quedar como experimental.
- La version se conserva historicamente.

### US-004 Calcular gramos de formula

Como usuaria, quiero ingresar un peso objetivo para ver cuantos gramos requiere cada ingrediente.

Criterios de aceptacion:

- Calcula gramos por ingrediente.
- Mantiene los porcentajes como fuente de verdad.
- Redondea de forma consistente.

## Epic 3 - Produccion

### US-005 Crear lote

Como Tea Blender, quiero registrar una elaboracion para crear un lote trazable.

Criterios de aceptacion:

- La fecha del lote es la fecha de elaboracion de la mezcla.
- El lote queda vinculado a una version exacta de formula.
- No permite producir si falta stock.
- Descuenta materias primas mediante movimientos.
- Crea un recurso tipo mezcla.
- Calcula el costo del lote con valores del momento.

### US-006 Consultar lote

Como usuaria, quiero ver el detalle de un lote para entender que se uso, cuando se elaboro y que costo tuvo.

Criterios de aceptacion:

- Muestra formula utilizada.
- Muestra consumo de ingredientes.
- Muestra movimientos relacionados.
- Muestra costo desglosado.

## Epic 4 - Ventas

### US-007 Registrar venta

Como usuaria, quiero registrar una venta con uno o varios productos para descontar stock y conservar el ingreso historico.

Criterios de aceptacion:

- Genera un codigo automatico unico.
- Requiere fecha, canal y medio de pago.
- Permite cliente opcional.
- Permite varias lineas de productos.
- No permite cantidades, precios ni descuentos negativos.
- Calcula subtotal, descuento total y total.
- Conserva el precio aplicado en el detalle historico.
- Descuenta stock mediante movimientos.
- Rechaza toda la venta si algun producto no tiene stock suficiente.

### US-008 Consultar historial de ventas

Como usuaria, quiero ver ventas nuevas e historicas en una sola pantalla para analizar lo vendido.

Criterios de aceptacion:

- Muestra fecha, codigo, canal, punto, cliente, productos, total, medio de pago y estado.
- Permite filtrar por fecha, canal, punto de venta, producto, medio de pago y estado.
- Distingue ventas del sistema de ventas importadas.
- Las ventas importadas no generan movimientos retroactivos.

### US-009 Anular venta

Como usuaria, quiero anular una venta confirmada para corregir errores sin borrar historial.

Criterios de aceptacion:

- No elimina la venta.
- Cambia estado a anulada.
- Registra fecha y motivo de anulacion.
- Genera movimientos inversos de inventario.
- Devuelve el stock al recurso vendido.
- No permite volver una venta anulada a confirmada.

### Casos de prueba de ventas

- Crear una venta valida con un producto.
- Crear una venta valida con varios productos.
- Rechazar una venta sin lineas.
- Rechazar cantidad cero.
- Rechazar cantidad negativa.
- Rechazar precio negativo.
- Rechazar stock insuficiente.
- Confirmar que una venta genera movimientos.
- Confirmar que el stock disminuye correctamente.
- Confirmar que una falla no deja venta parcial.
- Confirmar que una falla no deja movimientos parciales.
- Anular una venta confirmada.
- Confirmar movimientos inversos por anulacion.
- Confirmar que el stock vuelve al anular.
- Impedir editar o eliminar ventas confirmadas.
- Confirmar que el precio aplicado queda historico.
- Confirmar que ventas importadas no descuentan stock.
- Filtrar historial por fecha.
- Filtrar historial por canal.
- Filtrar historial por producto.
- Confirmar concurrencia para que dos ventas no consuman el mismo stock.

## Epic 5 - Compras

### US-010 Crear compra en borrador

Como usuaria, quiero registrar una compra con proveedor y lineas para dejar documentado lo comprado antes de confirmar stock.

Criterios de aceptacion:

- Requiere fecha y proveedor.
- Permite comprobante opcional.
- Permite observaciones opcionales.
- Requiere al menos una linea.
- Cada linea requiere recurso, cantidad, unidad y precio unitario.
- No permite cantidades, precios ni subtotales negativos.
- Calcula el total automaticamente.
- Una compra en borrador no modifica stock.

### US-011 Confirmar compra

Como usuaria, quiero confirmar una compra para aumentar el stock y registrar el costo unitario comprado.

Criterios de aceptacion:

- Una compra confirmada genera movimientos `purchase`.
- Cada movimiento queda referenciado a la compra.
- El stock aumenta por la cantidad comprada.
- El costo unitario queda guardado en el detalle y en costos del recurso.
- No permite confirmar dos veces la misma compra.
- Una compra confirmada no se edita directamente.

### Casos de prueba de compras

- Crear una compra en borrador.
- Confirmar que el borrador no modifica stock.
- Confirmar una compra.
- Confirmar que aumenta el stock.
- Confirmar que se genera movimiento de inventario.
- Confirmar que se guarda el costo unitario.
- Impedir confirmar dos veces.
- Rechazar cantidad cero.
- Rechazar cantidad negativa.
- Rechazar precio negativo.
