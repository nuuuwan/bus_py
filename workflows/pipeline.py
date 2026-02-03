from bus import Halt, Route


def main():
    Halt.build_all()
    Halt.draw_all()

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


if __name__ == "__main__":
    main()
