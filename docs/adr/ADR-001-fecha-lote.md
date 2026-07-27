# ADR-001 - Fecha del lote

## Estado

Aprobada

## Contexto

Durante la operacion real, la fecha impresa en el lote corresponde al dia en que se elaboro la mezcla. El envasado puede ocurrir el mismo dia o dias despues.

## Decision

La fecha del lote sera siempre la fecha de elaboracion de la mezcla.

## Consecuencias

- El envasado sera un evento posterior.
- Todas las unidades envasadas desde una misma mezcla conservaran el mismo lote.
- La trazabilidad se apoya en la elaboracion, no en el envasado.

