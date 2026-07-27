# MVP v0.1

## Objetivo

Que Eter Tempus pueda comenzar a registrar su operacion diaria desde el ERP, empezando por recursos, formulas y produccion.

## Epicas incluidas

### Epic 1 - Recursos

Permite registrar cualquier elemento que pueda comprarse, producirse, almacenarse, consumirse, envasarse, venderse o descartarse.

Tipos iniciales:

- Materia prima.
- Packaging.
- Producto.
- Mezcla.

### Epic 2 - Formulas

Permite crear formulas versionadas. La formula se almacena en porcentajes y se calcula en gramos segun el peso a elaborar.

### Epic 3 - Produccion

Permite crear un lote a partir de una formula activa. Al confirmar:

- Se crea el lote.
- Se consume materia prima.
- Se crea un recurso tipo mezcla.
- Se registran movimientos.
- Se calcula una fotografia inicial del costo.

### Epic 4 - Ventas

Permite registrar ventas reales desde el ERP. Al confirmar:

- Se genera un codigo automatico de venta.
- Se registran una o varias lineas de productos.
- Se conserva el precio aplicado en ese momento.
- Se descuenta stock mediante movimientos de inventario.
- Se impide vender si no hay stock suficiente.
- Se permite anular sin borrar la venta.

## Criterio de exito de v0.1

El flujo debe permitir:

```text
Crear materia prima
  -> Crear producto
  -> Crear formula
  -> Elaborar lote
  -> Cargar stock de producto terminado
  -> Registrar venta
  -> Ver movimientos generados
```
