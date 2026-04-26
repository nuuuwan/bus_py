from dataclasses import dataclass

from utils_future import IDMixin


@dataclass
class RoadSegment:
    road_id: str
    start_road_index: int
    end_road_index: int

    @property
    def id(self) -> str:
        return IDMixin.from_items(
            self.road_id,
            f"{self.start_road_index:03d}",
            f"{self.end_road_index:03d}",
        )
