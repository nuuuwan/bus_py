import os

import contextily as ctx
import matplotlib.pyplot as plt
from utils import JSONFile, Log

from googlemaps_utils import GoogleMapsUtils

log = Log("Route")


class Route:
    DIR_DATA_ROUTES = os.path.join("data", "routes")

    def __init__(
        self,
        route_num: str,
        direction: str,
        latlng_list: list[tuple],
    ):
        self.route_num = route_num
        self.direction = direction
        self.latlng_list = latlng_list

    @classmethod
    def get_file_path(cls, route_num: str, direction: str) -> str:
        return os.path.join(
            cls.DIR_DATA_ROUTES, f"{route_num}-{direction}.json"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Route":
        return cls(
            route_num=data["route_num"],
            direction=data["direction"],
            latlng_list=data["latlng_list"],
        )

    @classmethod
    def from_route_num(cls, route_num: str, direction: str) -> "Route":
        file_path = cls.get_file_path(route_num, direction=direction)
        data = JSONFile(file_path).read()
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "route_num": self.route_num,
            "direction": self.direction,
            "latlng_list": self.latlng_list,
        }

    def to_file(self) -> None:
        file_path = self.get_file_path(self.route_num, self.direction)
        os.makedirs(self.DIR_DATA_ROUTES, exist_ok=True)
        JSONFile(file_path).write(self.to_dict())

    @classmethod
    def build(
        cls,
        route_num: str,
        direction: str,
        start_location_name: str,
        end_location_name: str,
    ) -> "Route":
        file_path = cls.get_file_path(route_num, direction)
        if os.path.exists(file_path):
            log.warning(f"Route {route_num} already exists at {file_path}")
            return cls.from_route_num(route_num, direction)

        latlng_list = GoogleMapsUtils.get_route_latlng_list(
            start_location_name=start_location_name,
            end_location_name=end_location_name,
            route_num=route_num,
        )
        route = cls(
            route_num=route_num,
            direction=direction,
            latlng_list=latlng_list,
        )
        route.to_file()
        log.info(f"Built route {route_num} with {len(latlng_list)} points")
        return route

    def draw(self, output_path: str = None) -> None:
        """
        Plot the route on a map with OpenStreetMap basemap.

        Args:
            output_path: Optional path to save the plot. If None, displays interactively.
        """
        if not self.latlng_list:
            log.warning(f"No points to plot for route {self.route_num}")
            return

        # Extract latitudes and longitudes
        lats = [latlng[0] for latlng in self.latlng_list]
        lngs = [latlng[1] for latlng in self.latlng_list]

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 10))

        # Plot the route
        ax.plot(
            lngs,
            lats,
            "b-",
            linewidth=2,
            label=f"Route {self.route_num}",
            zorder=2,
        )
        ax.plot(lngs[0], lats[0], "go", markersize=10, label="Start", zorder=3)
        ax.plot(lngs[-1], lats[-1], "ro", markersize=10, label="End", zorder=3)

        # Add basemap
        try:
            ctx.add_basemap(
                ax,
                crs="EPSG:4326",
                source=ctx.providers.OpenStreetMap.Mapnik,
                zoom="auto",
                attribution="© OpenStreetMap contributors",
            )
        except Exception as e:
            log.warning(f"Could not add basemap: {e}")

        # Set labels and title
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title(
            f"Route {
                self.route_num} ({
                self.direction}) ({
                len(
                    self.latlng_list)} points)"
        )
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save or show
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            log.info(f"Route {self.route_num} map saved to {output_path}")
        else:
            plt.show()

        plt.close()
