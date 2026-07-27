# Siguientes Pasos

## Prioridad 1 - Conectar backend con PostgreSQL

1. Crear modelos SQLAlchemy.
2. Implementar repositorios.
3. Conectar los casos de uso a los repositorios reales.
4. Ejecutar el flujo completo con datos de seed.

## Prioridad 2 - Activar formularios del frontend

1. Guardar recursos desde la pantalla Recursos.
2. Crear formulas desde la pantalla Formulas.
3. Crear lote desde la pantalla Produccion.
4. Mostrar errores utiles cuando falte informacion.

## Prioridad 3 - Completar vertical del MVP

Flujo objetivo:

```text
Alta de materia prima
  -> Alta de producto
  -> Creacion de formula
  -> Elaboracion de lote
  -> Movimientos generados
  -> Stock calculado
```

## Riesgos a resolver pronto

- Definir estrategia de costos: ultimo costo, costo promedio o costo por lote de compra.
- Definir si packaging entra en v0.1 tecnica o v0.2.
- Definir formato final del numero de lote.
- Definir reglas de redondeo para gramos.

