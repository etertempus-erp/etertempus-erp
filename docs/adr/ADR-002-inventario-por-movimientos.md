# ADR-002 - Inventario por movimientos

## Estado

Aprobada

## Contexto

Guardar stock como un valor editable genera inconsistencias y dificulta la trazabilidad.

## Decision

El stock no se almacenara como dato manual. Se calculara desde movimientos de inventario.

## Consecuencias

- Toda entrada o salida debe generar movimientos.
- Los ajustes tambien deben registrarse como movimientos.
- El sistema puede reconstruir la historia completa de cada recurso.

