from bus import Halt, Route


def main():
    Halt.build_all()
    Halt.draw_all()

    for route_num, start_location1, end_location1, is_north_south in [
        (
            "101",
            "Pettah Bus Stop",
            "Maliban Junction Bus Stop",
            True,
        ),
        (
            "103",
            "Pettah Bus Stop",
            "Narehenpita Railway Bus Stop",
            True,
        ),
        (
            "120",
            "Colombo Central Bus Stand",
            "Piliyandala Bus Stand",
            True,
        ),
        ("138", "Pettah Bus Stop", "Homagama Bus Station", True),
        (
            "143",
            "Colombo Central Bus Stop",
            "Hanwella Bus Stand",
            False,
        ),
        (
            "144",
            "Colombo Central Bus Stop",
            "Rajagiriya Bus Stop",
            True,
        ),
        (
            "176",
            "Kotahena Bus Stop",
            "Karagampitiya Bus Station",
            True,
        ),
        (
            "177",
            "Kollupitiya Supermarket Bus Stop",
            "Kaduwela",
            False,
        ),
    ]:

        directions = (
            ["southbound", "northbound"]
            if is_north_south
            else ["eastbound", "westbound"]
        )
        for i_direction, direction in enumerate(directions, start=1):
            start_location, end_location = (
                [start_location1, end_location1]
                if (i_direction == 1)
                else [end_location1, start_location1]
            )
            route = Route.build(
                route_num,
                direction,
                start_location,
                end_location,
            )

            route.draw()

    Route.aggregate()


if __name__ == "__main__":
    main()
