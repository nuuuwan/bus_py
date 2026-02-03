"""Example script to draw a route on a map."""

from src.bus.core.route import Route

# Load an existing route
route = Route.from_route_num("138")

# Draw the route on a map (will display interactively)
route.draw()

# Or save to a file
# route.draw(output_path="route_138_map.png")
