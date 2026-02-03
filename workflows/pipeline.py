from bus import Halt, Route


def main():

    for route_num, direction, start_location, end_location in [
        ("138", "northbound", "Homagama Bus Station", "Pettah Bus Station"),
        ("138", "southbound", "Pettah Bus Station", "Homagama Bus Station"),
    ]:
        route = Route.build(
            route_num,
            direction,
            start_location,
            end_location,
        )
        route.draw()

    Halt.build_all()


if __name__ == "__main__":
    main()
