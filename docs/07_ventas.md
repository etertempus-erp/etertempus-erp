# Ventas v0.1

## Alcance implementado

Ventas permite registrar una venta confirmada con uno o varios productos. Cada venta genera:

- Codigo automatico.
- Detalle historico de productos, cantidades, precio, descuento y total.
- Movimiento negativo de inventario por cada producto vendido.
- Historial visible junto con las ventas importadas desde Excel.

## Flujo manual

1. Abrir `http://localhost:3000/ventas`.
2. Seleccionar fecha, canal y medio de pago.
3. Si el canal es feria o punto de venta, seleccionar punto de venta.
4. Agregar uno o varios productos.
5. Confirmar venta.

Si el producto no tiene stock suficiente, el sistema rechaza la venta completa y no descuenta nada.

## Anulacion

Una venta confirmada no se edita ni se borra.

Para corregir un error:

1. Abrir el historial.
2. Presionar la accion de anular.
3. Escribir el motivo.

El sistema marca la venta como anulada y genera movimientos inversos para devolver stock.

## Ventas historicas

Las ventas importadas desde Excel se muestran con origen `imported`.

Estas ventas son solo historicas:

- No descuentan stock.
- No pueden anularse desde el flujo nuevo.
- No generan movimientos retroactivos.

## Concurrencia

Al confirmar una venta, el backend bloquea las filas de los productos vendidos dentro de la transaccion. Esto evita que dos ventas simultaneas puedan consumir el mismo stock disponible.

## Deuda tecnica

El sistema todavia no controla producto terminado por lote porque falta implementar Envasado. Por eso, Ventas v0.1 descuenta directamente recursos de tipo `product`.

Cuando exista Envasado, Ventas debera evolucionar para:

- consumir stock por lote;
- aplicar FIFO por fecha de elaboracion;
- registrar que lote abastecio cada linea;
- dividir una linea entre varios lotes si es necesario.
