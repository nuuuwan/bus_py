from dataclasses import dataclass, field


@dataclass
class Bus:
    route_id: str
    road_segment_ids: list[str] = field(default_factory=list)
