import os

import contextily as ctx
import matplotlib.pyplot as plt
from utils import JSONFile, Log

from bus.core.Halt import Halt
from googlemaps_utils import GoogleMapsUtils

log = Log("Route")


class Route:
    DIR_DATA_ROUTES = os.path.join("data", "routes")
    DIR_IMAGES_ROUTES = os.path.join("images", "routes")

    def __init__(
        self,
        route_num: str,
        direction: str,
        halt_name_list: list[str],
        latlng_list: list[tuple],
    ):
        self.route_num = route_num
        self.direction = direction
        self.halt_name_list = halt_name_list
        self.latlng_list = latlng_list

    def __str__(self) -> str:
        return (
            f"Route ({self.route_num}-{self.direction} "
            f"{len(self.latlng_list)} points, "
            f"{len(self.halt_name_list)} halts)"
        )

    @classmethod
    def get_file_path(cls, route_num: str, direction: str) -> str:
        return os.path.join(
            cls.DIR_DATA_ROUTES, f"{route_num}-{direction}.json"
        )

    @property
    def image_path(self) -> str:
        return os.path.join(
            self.DIR_IMAGES_ROUTES, f"{self.route_num}-{self.direction}.png"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Route":
        return cls(
            route_num=data["route_num"],
            direction=data["direction"],
            halt_name_list=data["halt_name_list"],
            latlng_list=data["latlng_list"],
        )

    @classmethod
    def from_route_num(cls, route_num: str, direction: str) -> "Route":
        file_path = cls.get_file_path(route_num, direction=direction)
        data = JSONFile(file_path).read()
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "route_num": self.route_num,
            "direction": self.direction,
            "halt_name_list": self.halt_name_list,
            "latlng_list": self.latlng_list,
        }

    def to_file(self) -> None:
        file_path = self.get_file_path(self.route_num, self.direction)
        os.makedirs(self.DIR_DATA_ROUTES, exist_ok=True)
        JSONFile(file_path).write(self.to_dict())

    @classmethod
    def build(
        cls,
        route_num: str,
        direction: str,
        start_location_name: str,
        end_location_name: str,
    ) -> "Route":
        file_path = cls.get_file_path(route_num, direction)
        if os.path.exists(file_path):
            route = cls.from_route_num(route_num, direction)
            log.warning(f"{route} already exists.")
            return route

        latlng_list = GoogleMapsUtils.get_route_latlng_list(
            start_location_name=start_location_name,
            end_location_name=end_location_name,
            route_num=route_num,
        )

        halt_list = Halt.get_nearby_halts(latlng_list, max_distance_in_m=50)
        halt_name_list = [halt.name for halt in halt_list]

        route = cls(
            route_num=route_num,
            direction=direction,
            halt_name_list=halt_name_list,
            latlng_list=latlng_list,
        )
        route.to_file()
        log.info(route)
        return route

    def draw(self) -> None:
        lats = [latlng[0] for latlng in self.latlng_list]
        lngs = [latlng[1] for latlng in self.latlng_list]

        __, ax = plt.subplots(figsize=(12, 10))

        ax.plot(
            lngs,
            lats,
            "b-",
            linewidth=2,
            label=f"Route {self.route_num}",
            zorder=2,
        )

        ctx.add_basemap(
            ax,
            crs="EPSG:4326",
            source=ctx.providers.OpenStreetMap.Mapnik,
            zoom="auto",
            attribution="© OpenStreetMap contributors",
        )

        ax.set_title(
            f"Route {
                self.route_num} ({
                self.direction}) ({
                len(
                    self.latlng_list)} points)"
        )
        ax.legend()
        os.makedirs(self.DIR_IMAGES_ROUTES, exist_ok=True)
        plt.savefig(self.image_path, dpi=75, bbox_inches="tight")
        log.info(f"Wrote {self.image_path}")
