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
