from dataclasses import dataclass

from utils_future import IDMixin
from utils_future.String import String


@dataclass
class Road(IDMixin):
    name: str  # E.g. "Galle Road"
    direction: str  # E.g. "S", "N", "E", "W"

    @property
    def id(self) -> str:
        return f"{String.to_kebab_case(self.name)}-{self.direction.lower()}"
