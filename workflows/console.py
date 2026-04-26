#!/usr/bin/env python3
"""Console workflow for adding bus route data."""

import json
import os
import sys
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import googlemaps
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from bus.core.Halt import Halt
from bus.core.Road import Road
from bus.core.RoadSegment import RoadSegment
from utils_future.LatLng import LatLng

console = Console()

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "db")
HALTS_DIR = os.path.join(_DB_DIR, "halts")
ROADS_DIR = os.path.join(_DB_DIR, "roads")
ROAD_SEGMENTS_DIR = os.path.join(_DB_DIR, "road_segments")
ROUTES_DIR = os.path.join(_DB_DIR, "routes")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    for d in [HALTS_DIR, ROADS_DIR, ROAD_SEGMENTS_DIR, ROUTES_DIR]:
        os.makedirs(d, exist_ok=True)


def _load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _save_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    console.print(
        f"  [dim]Saved →[/dim] [green]{os.path.relpath(path)}[/green]"
    )


def _list_db_ids(dir_path: str) -> list[str]:
    if not os.path.exists(dir_path):
        return []
    return sorted(
        f.removesuffix(".json")
        for f in os.listdir(dir_path)
        if f.endswith(".json")
    )


def _geocode(halt_name: str, road_name: str) -> LatLng:
    """Return LatLng for a halt, using Google Maps or manual entry."""
    api_key = os.environ.get("GMAPS_API_KEY", "")
    if api_key:
        try:
            gmaps = googlemaps.Client(key=api_key)
            query = f"{halt_name}, {road_name}, Sri Lanka"
            results = gmaps.geocode(query)
            if results:
                loc = results[0]["geometry"]["location"]
                latlng = LatLng(lat=loc["lat"], lng=loc["lng"])
                console.print(
                    f"  [dim]Geocoded:[/dim] {latlng.lat:.6f}N, {latlng.lng:.6f}E"
                )
                maps_url = (
                    f"https://www.google.com/maps?q={latlng.lat},{latlng.lng}"
                )
                console.print(
                    f"  [dim]Opening in Google Maps for verification…[/dim]"
                )
                webbrowser.open(maps_url)
                return latlng
            console.print("[yellow]Geocoding returned no results.[/yellow]")
        except Exception as exc:
            console.print(f"[yellow]Geocoding error: {exc}[/yellow]")
    else:
        console.print(
            "[yellow]GOOGLE_MAPS_API_KEY not set — enter coordinates manually.[/yellow]"
        )

    lat = float(Prompt.ask("    Latitude"))
    lng = float(Prompt.ask("    Longitude"))
    return LatLng(lat=lat, lng=lng)


# ---------------------------------------------------------------------------
# Road
# ---------------------------------------------------------------------------


def _select_or_create_road() -> tuple[str, str]:
    """Return (road_id, road_name). Creates a new road (with halts) if needed."""
    existing = _list_db_ids(ROADS_DIR)

    if existing:
        table = Table(
            title="Roads in DB", show_header=True, header_style="bold cyan"
        )
        table.add_column("#", style="cyan", width=4)
        table.add_column("Road ID")
        for i, rid in enumerate(existing, 1):
            table.add_row(str(i), rid)
        console.print(table)

        raw = Prompt.ask(
            "Road (number to select, or [bold]New[/bold])", default="New"
        )
        if raw.strip().lower() != "new":
            try:
                idx = int(raw.strip()) - 1
                if 0 <= idx < len(existing):
                    road_id = existing[idx]
                    road_data = _load_json(
                        os.path.join(ROADS_DIR, f"{road_id}.json")
                    )
                    console.print(f"  Using road [bold]{road_id}[/bold]")
                    return road_id, road_data["name"]
            except (ValueError, FileNotFoundError):
                pass
            console.print(
                "[red]Invalid selection — creating a new road.[/red]"
            )
    else:
        console.print("[dim]No roads in DB yet.[/dim]")

    return _create_road()


def _create_road() -> tuple[str, str]:
    """Prompt for road name and halts, save to DB, return (road_id, road_name)."""
    road_name = Prompt.ask("Road Name")
    road = Road(name=road_name)
    road_id = road.id

    _save_json(os.path.join(ROADS_DIR, f"{road_id}.json"), {"name": road_name})

    # Collect halts
    console.print(
        f"\n[bold]Add halts for [cyan]{road_name}[/cyan] (leave blank to stop):[/bold]"
    )
    road_index = 0
    while True:
        halt_name = Prompt.ask(f"  Halt {road_index}", default="")
        if not halt_name.strip():
            break
        latlng = _geocode(halt_name.strip(), road_name)
        halt = Halt(
            road_id=road_id,
            road_index=road_index,
            name=halt_name.strip(),
            latlng=latlng,
        )
        _save_json(
            os.path.join(HALTS_DIR, f"{halt.id}.json"),
            {
                "road_id": road_id,
                "road_index": road_index,
                "name": halt_name.strip(),
                "latlng": {"lat": latlng.lat, "lng": latlng.lng},
            },
        )
        road_index += 1

    return road_id, road_name


# ---------------------------------------------------------------------------
# Road Segment
# ---------------------------------------------------------------------------


def _select_or_create_road_segment() -> str:
    """Return a road_segment_id. Creates a new one if needed."""
    existing = _list_db_ids(ROAD_SEGMENTS_DIR)

    if existing:
        table = Table(
            title="Road Segments in DB",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", style="cyan", width=4)
        table.add_column("Segment ID")
        for i, sid in enumerate(existing, 1):
            table.add_row(str(i), sid)
        console.print(table)

        raw = Prompt.ask(
            "RoadSegment (number to select, or [bold]New[/bold])",
            default="New",
        )
        if raw.strip().lower() != "new":
            try:
                idx = int(raw.strip()) - 1
                if 0 <= idx < len(existing):
                    seg_id = existing[idx]
                    console.print(f"  Using segment [bold]{seg_id}[/bold]")
                    return seg_id
            except ValueError:
                pass
            console.print(
                "[red]Invalid selection — creating a new road segment.[/red]"
            )
    else:
        console.print("[dim]No road segments in DB yet.[/dim]")

    return _create_road_segment()


def _create_road_segment() -> str:
    """Prompt for road and indices, save to DB, return segment_id."""
    road_id, _road_name = _select_or_create_road()

    # Derive sensible default for end index from existing halts on this road
    halt_ids = _list_db_ids(HALTS_DIR)
    road_halt_count = sum(1 for h in halt_ids if h.startswith(road_id + "-"))
    default_end = str(max(0, road_halt_count - 1))

    start = int(Prompt.ask("  Start road index", default="0"))
    end = int(Prompt.ask("  End road index", default=default_end))

    seg = RoadSegment(
        road_id=road_id, start_road_index=start, end_road_index=end
    )
    seg_data = {
        "road_id": road_id,
        "start_road_index": start,
        "end_road_index": end,
    }
    _save_json(os.path.join(ROAD_SEGMENTS_DIR, f"{seg.id}.json"), seg_data)
    return seg.id


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

_DIRECTION_NAMES = {
    "N": "northbound",
    "S": "southbound",
    "E": "eastbound",
    "W": "westbound",
}


def _new_route() -> None:
    """Interactively create a full route and save all data to DB."""
    console.print(Panel("[bold]New Route[/bold]", expand=False))

    code = Prompt.ask("Route Code")

    direction = ""
    while direction not in _DIRECTION_NAMES:
        direction = Prompt.ask("Route Direction [N|S|E|W]").strip().upper()
        if direction not in _DIRECTION_NAMES:
            console.print("[red]Must be one of N, S, E, W.[/red]")

    road_segment_ids: list[str] = []

    console.print("\n[bold]Add road segments (at least one required):[/bold]")
    while True:
        seg_id = _select_or_create_road_segment()
        road_segment_ids.append(seg_id)
        console.print(
            f"  [green]✓[/green] Added segment [bold]{seg_id}[/bold]"
        )

        more = Prompt.ask("\nAdd another road segment? [Y/n]", default="Y")
        if more.strip().lower() == "n":
            break

    route_id = f"{code}-{_DIRECTION_NAMES[direction]}"
    route_data = {
        "code": code,
        "direction": direction,
        "road_segment_id_list": road_segment_ids,
    }
    _save_json(os.path.join(ROUTES_DIR, f"{route_id}.json"), route_data)

    console.print(
        Panel(
            f"[bold green]Route {code} ({_DIRECTION_NAMES[direction]}) created "
            f"with {len(road_segment_ids)} segment(s).[/bold green]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------


def main() -> None:
    _ensure_dirs()
    console.print(
        Panel("[bold blue]Bus Route Data Entry[/bold blue]", expand=False)
    )

    while True:
        console.print()
        action = Prompt.ask(
            "Action",
            choices=["New Route", "quit"],
            default="New Route",
        )
        if action == "quit":
            console.print("[dim]Bye.[/dim]")
            break
        if action == "New Route":
            _new_route()


if __name__ == "__main__":
    main()
