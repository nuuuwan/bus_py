from dataclasses import dataclass

from utils_future import IDMixin, LatLng, String


@dataclass
class Halt:
    road_id: int  # E.g. 'galle-road'
    road_index: int  # E.g. 2
    name: str  # E.g. "Colombo Museum"
    latlng: LatLng  # E.g. LatLng(6.9271, 79.8612)

    @property
    def id(self) -> str:
        # E.g. "galle-road-002-colombo-museum"
        return IDMixin.from_items(
            self.road_id,
            String.to_kebab_case(self.name),
        )
