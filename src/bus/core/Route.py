from dataclasses import dataclass


@dataclass
class Route:
    code: str  # E.g. 138
    direction: str  # E.g. Southbound
    road_segment_id_list: list[
        str
    ]  # E.g. ["galle-road-000-002", "galle-road-002-004", ...]
