import os

import googlemaps
import polyline


class GoogleMapsUtils:
    @staticmethod
    def get_route_latlng_list(
        route_num: str,
        start_location_name: str,
        end_location_name: str,
    ) -> list[tuple]:
        api_key = os.environ.get("GMAPS_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY environment variable not set"
            )

        gmaps = googlemaps.Client(key=api_key)

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

        selected_route = None
        for route in directions_result:
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    transit_details = step.get("transit_details", {})
                    line = transit_details.get("line", {})
                    short_name = line.get("short_name", "")
                    if short_name == route_num:
                        selected_route = route
                        break
                if selected_route:
                    break
            if selected_route:
                break

        if not selected_route:
            selected_route = directions_result[0]

        encoded_polyline = selected_route["overview_polyline"]["points"]
        decoded_latlng_list = polyline.decode(encoded_polyline)
        return decoded_latlng_list
