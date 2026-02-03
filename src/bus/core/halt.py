import os
from functools import cache
from math import asin, cos, radians, sin, sqrt

from utils import JSONFile, Log

from googlemaps_utils import GoogleMapsUtils

log = Log("Halt")


class Halt:
    HALTS_DATA_PATH = os.path.join("data", "halts.json")

    def __init__(self, name: str, latlng: tuple[float, float]):
        self.name = name
        self.latlng = latlng

    @classmethod
    def from_dict(cls, data: dict) -> "Halt":
        return cls(name=data["name"], latlng=tuple(data["latlng"]))

    def to_dict(self) -> dict:
        return {"name": self.name, "latlng": list(self.latlng)}

    @classmethod
    @cache
    def list_all(cls) -> list["Halt"]:
        data = JSONFile(cls.HALTS_DATA_PATH).read()
        return [cls.from_dict(item) for item in data]

    @classmethod
    def build_all(cls):
        if os.path.exists(cls.HALTS_DATA_PATH):
            log.warning(f"{cls.HALTS_DATA_PATH} exists. Skipping build.")
            return cls.list_all()

        halt_data_list = GoogleMapsUtils.get_halts()
        halts = [cls.from_dict(data) for data in halt_data_list]
        JSONFile(cls.HALTS_DATA_PATH).write(
            [halt.to_dict() for halt in halts]
        )
        log.info(
            f"Built {len(halts)} halts and saved to {cls.HALTS_DATA_PATH}."
        )
        return halts

    @staticmethod
    def __calculate_distance_in_m(
        latlng1: tuple[float, float], latlng2: tuple[float, float]
    ) -> float:
        lat1, lng1 = radians(latlng1[0]), radians(latlng1[1])
        lat2, lng2 = radians(latlng2[0]), radians(latlng2[1])

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371_000

        return c * r

    @classmethod
    def get_closest_halt(
        cls, latlng: tuple[float, float], max_distance_in_m: float
    ) -> "Halt":
        halts = cls.list_all()
        if not halts:
            return None

        closest_halt = None
        min_distance = float("inf")

        for halt in halts:
            distance = cls.__calculate_distance_in_m(latlng, halt.latlng)
            if distance < min_distance:
                min_distance = distance
                closest_halt = halt

        if min_distance <= max_distance_in_m:
            return closest_halt

        return None

    @classmethod
    def get_nearby_halts(
        cls, latlng_list: list[tuple[float, float]], max_distance_in_m: float
    ) -> list["Halt"]:
        halts = cls.list_all()
        if not halts or not latlng_list:
            return []

        nearby_halts = []

        for latlng in latlng_list:
            for halt in halts:
                distance = cls.__calculate_distance_in_m(latlng, halt.latlng)
                if distance <= max_distance_in_m:
                    nearby_halts.append(halt)
                    break

        return nearby_halts
