import os

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
