import os

from utils import JSONFile

from .halt import Halt
from .segment import Segment


class Route:

    def __init__(
        self,
        route_num: str,
        halt_list: list[Halt],
        segment_list: list[Segment],
    ):
        self.route_num = route_num
        self.halt_list = halt_list
        self.segment_list = segment_list

    @classmethod
    def from_dict(cls, data: dict) -> "Route":
        return cls(
            route_num=data["route_num"],
            halt_list=[Halt.from_dict(h) for h in data["halt_list"]],
            segment_list=[Segment.from_dict(s) for s in data["segment_list"]],
        )

    @classmethod
    def list_all(cls) -> list["Route"]:
        file_path = os.path.join("data", "routes.json")
        data = JSONFile(file_path).read()
        return [cls.from_dict(item) for item in data]
