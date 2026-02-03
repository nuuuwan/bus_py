import os
import time

import googlemaps
import polyline


class GoogleMapsUtils:
    @staticmethod
    def __get_gmaps_client() -> googlemaps.Client:
        api_key = os.environ.get("GMAPS_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY environment variable not set"
            )
        return googlemaps.Client(key=api_key)

    @staticmethod
    def __get_directions(
        gmaps: googlemaps.Client,
        start_location_name: str,
        end_location_name: str,
    ) -> list[dict]:
        directions_result = gmaps.directions(
            origin=start_location_name,
            destination=end_location_name,
            mode="transit",
            alternatives=True,
        )

        if not directions_result:
            raise ValueError(
                "No route found from"
                + f" {start_location_name} to {end_location_name}"
            )

        return directions_result

    @staticmethod
    def __find_matching_route(
        directions_result: list[dict], route_num: str
    ) -> dict:
        for route in directions_result:
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    transit_details = step.get("transit_details", {})
                    line = transit_details.get("line", {})
                    short_name = line.get("short_name", "")
                    if short_name == route_num:
                        return route

        return directions_result[0]

    @staticmethod
    def __decode_route_polyline(route: dict) -> list[tuple]:
        encoded_polyline = route["overview_polyline"]["points"]
        return polyline.decode(encoded_polyline)

    @staticmethod
    def get_route_latlng_list(
        route_num: str,
        start_location_name: str,
        end_location_name: str,
    ) -> list[tuple]:
        gmaps = GoogleMapsUtils.__get_gmaps_client()
        directions_result = GoogleMapsUtils.__get_directions(
            gmaps, start_location_name, end_location_name
        )
        selected_route = GoogleMapsUtils.__find_matching_route(
            directions_result, route_num
        )
        return GoogleMapsUtils.__decode_route_polyline(selected_route)

    @staticmethod
    def __extract_halt_from_place(place: dict) -> dict:
        name = place.get("name", "Unknown")
        location = place.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        if lat is None or lng is None:
            return None

        return {"name": name, "latlng": [lat, lng]}

    @staticmethod
    def __extract_halts_from_results(places_result: dict) -> list[dict]:
        halts = []
        for place in places_result.get("results", []):
            halt = GoogleMapsUtils.__extract_halt_from_place(place)
            if halt:
                halts.append(halt)
        return halts

    @staticmethod
    def __fetch_paginated_halts(
        gmaps: googlemaps.Client, places_result: dict
    ) -> list[dict]:
        halts = []
        while "next_page_token" in places_result:
            time.sleep(2)
            places_result = gmaps.places_nearby(
                page_token=places_result["next_page_token"]
            )
            page_halts = GoogleMapsUtils.__extract_halts_from_results(
                places_result
            )
            halts.extend(page_halts)
        return halts

    @staticmethod
    def get_halts(
        center_lat: float = 6.9271,
        center_lng: float = 79.8612,
        radius: int = 10000,
    ) -> list[dict]:
        gmaps = GoogleMapsUtils.__get_gmaps_client()
        location = (center_lat, center_lng)

        places_result = gmaps.places_nearby(
            location=location, radius=radius, type="bus_station"
        )

        halts = GoogleMapsUtils.__extract_halts_from_results(places_result)
        paginated_halts = GoogleMapsUtils.__fetch_paginated_halts(
            gmaps, places_result
        )
        halts.extend(paginated_halts)

        return halts
