# ADR-003 - Recurso como entidad base

## Estado

Aprobada para v0.1

## Contexto

Materias primas, packaging, productos y mezclas comparten una caracteristica central: pueden existir en inventario y moverse.

## Decision

Se usara una entidad base llamada recurso para todo elemento inventariable.

## Consecuencias

- Un unico motor de movimientos sirve para todos los tipos.
- La base puede crecer hacia nuevos tipos sin redisenar el inventario.
- Las particularidades de cada tipo se agregaran con tablas especializadas cuando sea necesario.

