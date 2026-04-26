from dataclasses import dataclass

from utils_future import IDMixin


@dataclass
class Road(IDMixin):
    name: str  # E.g. "Galle Road"
