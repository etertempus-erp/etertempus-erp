# Reglas de Negocio

## Recursos

- Todo elemento inventariable es un recurso.
- Los recursos pueden ser materia prima, packaging, producto o mezcla.
- El stock no se edita manualmente; se calcula desde movimientos.

## Formulas

- La formula se almacena en porcentaje.
- Los gramos se calculan segun el peso objetivo.
- Una formula puede tener versiones.
- Un lote siempre queda asociado a la version usada al momento de elaborarlo.
- Una formula activa no elimina versiones anteriores.

## Lotes

- El lote nace al elaborar la mezcla.
- La fecha del lote es la fecha de elaboracion, no la fecha de envasado.
- La mezcla elaborada es un recurso inventariable.
- Una mezcla puede tener multiples destinos futuros: envasado, consumo interno, degustacion, desarrollo o descarte.

## Movimientos

- Todo cambio de inventario se registra como movimiento.
- Todo movimiento debe tener recurso, cantidad, tipo, fecha y origen funcional.
- Nada desaparece sin motivo.
- El inventario actual se calcula sumando entradas y restando salidas.

## Costos

- El costo de un lote debe conservar una fotografia del momento de elaboracion.
- El costo de producto no es solo materia prima; debe poder incorporar packaging y mano de obra en iteraciones posteriores.
- Todo costo calculado debe poder explicarse por componentes.

## Ventas

- Una venta confirmada no se edita ni se borra.
- Si una venta tiene un error, se anula y se crea una nueva.
- Toda venta debe tener al menos un producto.
- El canal y el medio de pago son obligatorios.
- El punto de venta es obligatorio cuando el canal corresponde a feria o punto de venta.
- El cliente es opcional.
- El total se calcula desde las lineas y no se escribe manualmente.
- El precio aplicado queda guardado en la linea de venta, aunque luego cambie la lista de precios.
- Una venta confirmada descuenta stock con movimientos negativos de tipo `sale`.
- Una anulacion devuelve stock con movimientos positivos de tipo `sale_cancellation`.
- Las ventas historicas importadas se muestran para consulta, pero no descuentan stock retroactivamente.

## Limitacion actual de lotes en ventas

- El sistema ya registra lotes de mezcla, pero todavia no tiene implementado el envasado que transforma mezcla en producto terminado por lote.
- Por esa razon, Ventas v0.1 descuenta el recurso de tipo `product` directamente.
- La trazabilidad FIFO por lote queda pendiente para la vertical de Envasado.

## Compras

- Una compra puede estar en borrador o confirmada.
- Una compra en borrador no modifica stock.
- Una compra confirmada aumenta stock con movimientos positivos de tipo `purchase`.
- Cada movimiento de compra queda vinculado a la compra que lo genero.
- La compra debe tener fecha, proveedor y al menos una linea.
- Cada linea debe tener recurso, cantidad mayor a cero, unidad y precio unitario mayor o igual a cero.
- El total de la compra se calcula desde las lineas.
- Una compra confirmada no se edita directamente.
- La anulacion de compras queda pendiente para una version posterior mediante movimiento inverso.
