import math
from dataclasses import dataclass


@dataclass
class LatLng:
    lat: float
    lng: float

    def distance_m(self, other: "LatLng") -> float:
        """Haversine distance in metres between two LatLng points."""
        R = 6_371_000
        lat1, lng1 = math.radians(self.lat), math.radians(self.lng)
        lat2, lng2 = math.radians(other.lat), math.radians(other.lng)
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))

    def to_kebab_case(self) -> str:
        return f"{self.lat:.6f}N-{self.lng:.6f}E"
