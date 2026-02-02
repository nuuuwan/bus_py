import os

from utils import JSONFile


class Segment:

    def __init__(self, name: str, latlng_list: list[tuple[float, float]]):
        self.name = name
        self.latlng_list = latlng_list

    @classmethod
    def from_dict(cls, data: dict) -> "Segment":
        """Create a Segment instance from a dictionary."""
        return cls(
            name=data["name"],
            latlng_list=[tuple(ll) for ll in data["latlng_list"]],
        )

    @classmethod
    def list_all(cls) -> list["Segment"]:
        file_path = os.path.join("data", "segments.json")
        data = JSONFile(file_path).read()
        return [cls.from_dict(item) for item in data]
