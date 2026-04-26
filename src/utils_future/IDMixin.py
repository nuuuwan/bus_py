from utils_future.String import String


class IDMixin:
    @property
    def id(self) -> str:
        return String.to_kebab_case(self.name)

    @staticmethod
    def from_items(*items: list[str]) -> str:
        return "-".join(items)
