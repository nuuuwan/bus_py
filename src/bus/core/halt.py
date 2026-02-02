import os

from utils import JSONFile


class Halt:

    def __init__(self, name: str, latlng: tuple[float, float]):
        self.name = name
        self.latlng = latlng

    @classmethod
    def from_dict(cls, data: dict) -> "Halt":
        return cls(name=data["name"], latlng=tuple(data["latlng"]))

    @classmethod
    def list_all(cls) -> list["Halt"]:
        file_path = os.path.join("data", "halts.json")
        data = JSONFile(file_path).read()
        return [cls.from_dict(item) for item in data]
