import os

from utils import JSONFile, Log

from overpass_utils import OverpassUtils

log = Log("Route")


class Route:
    DIR_DATA_ROUTES = os.path.join("data", "routes")

    def __init__(
        self,
        route_num: str,
        latlng_list: list[tuple],
    ):
        self.route_num = route_num
        self.latlng_list = latlng_list

    @classmethod
    def get_file_path(cls, route_num: str) -> str:
        return os.path.join(cls.DIR_DATA_ROUTES, f"{route_num}.json")

    @classmethod
    def from_dict(cls, data: dict) -> "Route":
        return cls(
            route_num=data["route_num"],
            latlng_list=data["latlng_list"],
        )

    @classmethod
    def from_route_num(cls, route_num: str) -> "Route":
        file_path = cls.get_file_path(route_num)
        data = JSONFile(file_path).read()
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "route_num": self.route_num,
            "latlng_list": self.latlng_list,
        }

    def to_file(self) -> None:
        file_path = self.get_file_path(self.route_num)
        os.makedirs(self.DIR_DATA_ROUTES, exist_ok=True)
        JSONFile(file_path).write(self.to_dict())

    @classmethod
    def build(cls, route_num: str) -> bool:
        file_path = cls.get_file_path(route_num)
        if os.path.exists(file_path):
            log.warning(f"Route {route_num} already exists at {file_path}")
            return False

        latlng_list = OverpassUtils.get_route_latlng_list(route_num)
        route = cls(
            route_num=route_num,
            latlng_list=latlng_list,
        )
        route.to_file()
        log.info(f"Built route {route_num} with {len(latlng_list)} points")
        return True
