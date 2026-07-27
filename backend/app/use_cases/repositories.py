from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.formulas.entities import Formula
from app.domain.production.entities import InventoryMovementDraft
from app.domain.resources.entities import Resource, ResourceType, UnitType


class ResourceRepository(ABC):
    @abstractmethod
    def create(
        self,
        organization_id: UUID,
        code: str,
        name: str,
        type: ResourceType,
        unit: UnitType,
        minimum_stock: Decimal,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    def list(self, organization_id: UUID, type: ResourceType | None = None) -> list[Resource]:
        raise NotImplementedError


class FormulaRepository(ABC):
    @abstractmethod
    def get(self, formula_id: UUID) -> Formula:
        raise NotImplementedError

    @abstractmethod
    def create(self, formula: Formula) -> UUID:
        raise NotImplementedError


class ProductionRepository(ABC):
    @abstractmethod
    def next_batch_number(self, organization_id: UUID) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_mix_resource(
        self,
        organization_id: UUID,
        batch_number: str,
        product_resource_id: UUID,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    def create_batch_with_movements(
        self,
        organization_id: UUID,
        batch_number: str,
        elaboration_date: date,
        product_resource_id: UUID,
        formula_id: UUID,
        mix_resource_id: UUID,
        target_weight: Decimal,
        movements: list[InventoryMovementDraft],
        notes: str | None = None,
    ) -> UUID:
        raise NotImplementedError
