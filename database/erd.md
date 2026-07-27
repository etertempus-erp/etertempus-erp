# ERD inicial - Eter ERP v0.1

```mermaid
erDiagram
    organizations ||--o{ resources : owns
    organizations ||--o{ formulas : owns
    organizations ||--o{ production_batches : owns
    organizations ||--o{ inventory_movements : owns
    organizations ||--o{ sales : owns

    resources ||--o{ formula_items : "used as ingredient"
    resources ||--o{ formulas : "product target"
    formulas ||--o{ formula_items : contains
    formulas ||--o{ production_batches : used_by
    resources ||--o{ production_batches : "product resource"
    resources ||--o{ production_batches : "mix resource"
    production_batches ||--o{ inventory_movements : generates
    resources ||--o{ inventory_movements : moves
    sales_channels ||--o{ sales : classifies
    payment_methods ||--o{ sales : paid_with
    points_of_sale ||--o{ sales : occurs_at
    sales ||--o{ sale_details : contains
    resources ||--o{ sale_details : sold_as
    sale_details ||--o{ sale_inventory_movements : traces
    inventory_movements ||--o{ sale_inventory_movements : generated_by

    organizations {
        uuid id PK
        text name
        timestamptz created_at
        timestamptz updated_at
        boolean active
    }

    resources {
        uuid id PK
        uuid organization_id FK
        text code
        text name
        resource_type type
        unit_type unit
        numeric minimum_stock
        boolean active
        timestamptz created_at
        timestamptz updated_at
    }

    formulas {
        uuid id PK
        uuid organization_id FK
        uuid product_resource_id FK
        text name
        integer version
        formula_status status
        boolean active_version
        text notes
        timestamptz created_at
        timestamptz updated_at
    }

    formula_items {
        uuid id PK
        uuid formula_id FK
        uuid ingredient_resource_id FK
        numeric percentage
        integer sort_order
    }

    production_batches {
        uuid id PK
        uuid organization_id FK
        text batch_number
        date elaboration_date
        uuid product_resource_id FK
        uuid formula_id FK
        uuid mix_resource_id FK
        numeric target_weight
        unit_type unit
        batch_status status
        numeric ingredient_cost_snapshot
        text notes
        timestamptz created_at
        timestamptz updated_at
    }

    inventory_movements {
        uuid id PK
        uuid organization_id FK
        uuid resource_id FK
        uuid production_batch_id FK
        movement_type type
        numeric quantity
        unit_type unit
        numeric unit_cost_snapshot
        text reason
        timestamptz occurred_at
        timestamptz created_at
    }

    sales {
        uuid id PK
        uuid organization_id FK
        text code
        date sale_date
        uuid channel_id FK
        uuid point_of_sale_id FK
        text customer_name
        uuid payment_method_id FK
        sale_status status
        numeric subtotal
        numeric discount_total
        numeric total
        text source
        timestamptz confirmed_at
        timestamptz cancelled_at
    }

    sale_details {
        uuid id PK
        uuid organization_id FK
        uuid sale_id FK
        uuid resource_id FK
        numeric quantity
        numeric unit_price
        numeric discount
        numeric line_total
    }
```

## Lectura del modelo

- `resources` es la entidad base para todo lo inventariable.
- Una formula puede pertenecer a un producto o quedar como experimental si `product_resource_id` es nulo.
- `formula_items.percentage` es la fuente de verdad de la receta.
- Al crear un lote se genera un recurso tipo `mix`, que representa la mezcla elaborada.
- El stock actual se calcula desde `inventory_movements`.
- Los movimientos de consumo de materia prima se guardan con cantidad negativa.
- Los movimientos de creacion de mezcla se guardan con cantidad positiva.
- Una venta confirmada descuenta recursos de tipo `product` mediante movimientos `sale`.
- Una venta anulada devuelve stock mediante movimientos `sale_cancellation`.
- Ventas v0.1 no consume FIFO por lote porque el envasado por lote aun no esta implementado.
