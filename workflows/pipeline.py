from bus import Halt, Route


def main():
    Halt.build_all()
    Halt.draw_all()

    for route_num, direction, start_location, end_location in [
        # 101
        (
            "101",
            "southbound",
            "Pettah Bus Stop",
            "Maliban Junction Bus Stop",
        ),
        (
            "101",
            "northbound",
            "Maliban Junction Bus Stop",
            "Pettah Bus Stop",
        ),
        # 103
        (
            "103",
            "southbound",
            "Pettah Bus Stop",
            "Narehenpita Railway Bus Stop",
        ),
        (
            "103",
            "northbound",
            "Narehenpita Railway Bus Stop",
            "Pettah Bus Stop",
        ),
        # 138
        ("138", "southbound", "Pettah Bus Stop", "Homagama Bus Station"),
        ("138", "northbound", "Homagama Bus Station", "Pettah Bus Stop"),
        # 176
        (
            "176",
            "southbound",
            "Kotahena Bus Stop",
            "Karagampitiya Bus Station",
        ),
        (
            "176",
            "northbound",
            "Karagampitiya Bus Station",
            "Kotahena Bus Stop",
        ),
        # 177
        (
            "177",
            "eastbound",
            "Kollupitiya Supermarket Bus Stop",
            "Kaduwela",
        ),
        (
            "177",
            "northbound",
            "Kaduwela",
            "Kollupitiya Supermarket Bus Stop",
        ),
    ]:
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
