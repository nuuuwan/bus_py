import os
import warnings
from functools import cache
from math import asin, cos, radians, sin, sqrt

import contextily as ctx
import matplotlib.pyplot as plt
from utils import JSONFile, Log

from googlemaps_utils import GoogleMapsUtils

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

log = Log("Halt")


class Halt:
    HALTS_DATA_PATH = os.path.join("data", "halts.json")
    DIR_IMAGES_HALTS = os.path.join("images", "halts")

    def __init__(self, id:str, name: str, latlng: tuple[float, float]):
        self.id = id
        assert id == self.get_id(name, latlng), f"ID mismatch: {id} != {self.get_id(name, latlng)}"
        self.name = name
        self.latlng = latlng


    @classmethod 
    def get_id(cls, name: str, latlng: tuple[float, float]) -> str:
        name_kebab = name.lower().replace(" ", "-").replace('.', '')
        return f"{name_kebab}-{latlng[0]:.4f}N-{latlng[1]:.4f}E"

    @classmethod
    def from_dict(cls, data: dict) -> "Halt":
        if 'id' not in data:
            data['id'] = cls.get_id(data['name'], tuple(data['latlng']))
        return cls(id=data["id"], name=data["name"], latlng=tuple(data["latlng"]))

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "latlng": list(self.latlng)}
    
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

        seen_ids = set()
        unique_halt_data_list = []
        for halt_data in halt_data_list:
            id = halt_data["id"]
            if id not in seen_ids:
                seen_ids.add(id)
                unique_halt_data_list.append(halt_data)

        halts = [cls.from_dict(data) for data in unique_halt_data_list]
        JSONFile(cls.HALTS_DATA_PATH).write(
            [halt.to_dict() for halt in halts]
        )
        log.info(
            f"Built {
                len(halts)} unique halts from {
                len(halt_data_list)} total,"
            + f" saved to {cls.HALTS_DATA_PATH}."
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
        nearby_halts = []

        for latlng in latlng_list:
            for halt in halts:
                if halt in nearby_halts:
                    continue
                distance = cls.__calculate_distance_in_m(latlng, halt.latlng)
                if distance <= max_distance_in_m:
                    nearby_halts.append(halt)

        return nearby_halts

    @classmethod
    def draw_all(cls) -> None:
        halts = cls.list_all()
        if not halts:
            log.warning("No halts to draw")
            return

        lats = [halt.latlng[0] for halt in halts]
        lngs = [halt.latlng[1] for halt in halts]

        __, ax = plt.subplots(figsize=(12, 10))

        ax.scatter(lngs, lats, c="red", s=50, zorder=3, label="Bus Halts")

        for halt in halts:
            ax.annotate(
                halt.name,
                xy=(halt.latlng[1], halt.latlng[0]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=6,
                zorder=4,
            )

        ctx.add_basemap(
            ax,
            crs="EPSG:4326",
            source=ctx.providers.OpenStreetMap.Mapnik,
            zoom="auto",
            attribution="© OpenStreetMap contributors",
        )

        ax.set_title(f"Bus Halts ({len(halts)} halts)")
        ax.legend()

        image_path = os.path.join(cls.DIR_IMAGES_HALTS, "all_halts.png")
        os.makedirs(cls.DIR_IMAGES_HALTS, exist_ok=True)
        plt.savefig(image_path, dpi=75, bbox_inches="tight")
        log.info(f"Wrote {image_path}")


    @classmethod
    def add_new_halt(cls, name: str, latlng: tuple[float, float]):
        halts = cls.list_all()
        halt_dicts = [h.to_dict() for h in halts]
        
        new_id = cls.get_id(name, latlng)
        
        if any(h['id'] == new_id for h in halt_dicts):
            log.warning(f"Halt {name} already exists")
            return
        
        new_halt = cls(id=new_id, name=name, latlng=latlng)
        halt_dicts.append(new_halt.to_dict())
        
        halt_dicts.sort(key=lambda x: x['name'])
        
        cls.__cleanup_halt_dicts(halt_dicts)
        
        JSONFile(cls.HALTS_DATA_PATH).write(halt_dicts)
        log.info(f"Added halt {name} at {latlng}")

    @classmethod
    def __cleanup_halt_dicts(cls, halt_dicts):
        for halt_dict in halt_dicts:
            lat, lng = halt_dict['latlng']
            halt_dict['latlng'] = [round(lat, 4), round(lng, 4)]

        