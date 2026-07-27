from decimal import Decimal
from uuid import UUID

from app.domain.resources.entities import ResourceType, UnitType
from app.use_cases.repositories import ResourceRepository


class CreateResource:
    def __init__(self, resources: ResourceRepository) -> None:
        self.resources = resources

    def execute(
        self,
        organization_id: UUID,
        code: str,
        name: str,
        type: ResourceType,
        unit: UnitType,
        minimum_stock: Decimal,
    ) -> UUID:
        return self.resources.create(
            organization_id=organization_id,
            code=code.strip(),
            name=name.strip(),
            type=type,
            unit=unit,
            minimum_stock=minimum_stock,
        )

