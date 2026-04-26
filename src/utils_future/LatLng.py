from dataclasses import dataclass


@dataclass
class LatLng:
    lat: float
    lng: float

    def to_kebab_case(self) -> str:
        return f"{self.lat:.6f}N-{self.lng:.6f}E"
