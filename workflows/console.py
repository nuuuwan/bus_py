#!/usr/bin/env python3
"""Console workflow for adding bus route data."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from bus.core.Halt import Halt
from bus.core.Road import Road
from bus.core.RoadSegment import RoadSegment
from utils_future.LatLng import LatLng
from utils_future.String import String

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
    """Prompt for comma-separated lat,lng and open in Google Maps to verify."""
    if halt_name.startswith("&"):
        cross = halt_name[1:].strip()
        label = f"{road_name} & {cross}"
    else:
        label = f"{halt_name}, {road_name}"

    while True:
        raw = Prompt.ask(
            f"  LatLng for [cyan]{label}[/cyan] (lat, lng)"
        ).strip()
        parts = raw.split(",")
        if len(parts) == 2:
            try:
                lat, lng = float(parts[0].strip()), float(parts[1].strip())
                latlng = LatLng(lat=lat, lng=lng)
                return latlng
            except ValueError:
                pass
        console.print(
            "[red]Enter as two numbers separated by a comma, e.g. 6.9171, 79.8656[/red]"
        )


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
    while True:
        road_name = Prompt.ask("Road Name").strip()
        last_word = road_name.split()[-1] if road_name else ""
        if len(last_word) == 2:
            break
        console.print(
            f"[red]Road name must end with a two-character word "
            f"(e.g. 'Rd', 'St', 'Dr'). Got '[bold]{last_word}[/bold]'.[/red]"
        )
    road = Road(name=road_name)
    road_id = road.id

    _save_json(os.path.join(ROADS_DIR, f"{road_id}.json"), {"name": road_name})

    # Collect halts
    console.print(
        f"\n[bold]Add halts for [cyan]{road_name}[/cyan] (leave blank to stop):[/bold]"
    )
    road_index = 0
    existing_halt_ids = _list_db_ids(HALTS_DIR)
    while True:
        halt_name = Prompt.ask(f"  Halt {road_index}", default="")
        if not halt_name.strip():
            break
        # Duplicate check: road already has a halt with this name
        candidate_id = f"{road_id}-{String.to_kebab_case(halt_name.strip())}"
        if candidate_id in existing_halt_ids:
            console.print(
                f"  [red]Halt '[bold]{halt_name.strip()}[/bold]' already exists on this road — skipped.[/red]"
            )
            road_index += 1
            continue
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
# Add segments to existing route
# ---------------------------------------------------------------------------


def _select_route() -> tuple[str, dict] | None:
    """Prompt user to pick an existing route. Returns (route_id, route_data) or None."""
    existing = _list_db_ids(ROUTES_DIR)
    if not existing:
        console.print("[yellow]No routes in DB yet.[/yellow]")
        return None

    table = Table(
        title="Routes in DB", show_header=True, header_style="bold cyan"
    )
    table.add_column("#", style="cyan", width=4)
    table.add_column("Route ID")
    table.add_column("Segments")
    for i, rid in enumerate(existing, 1):
        try:
            data = _load_json(os.path.join(ROUTES_DIR, f"{rid}.json"))
            segs = ", ".join(data.get("road_segment_id_list", []))
        except (FileNotFoundError, KeyError):
            segs = ""
        table.add_row(str(i), rid, segs)
    console.print(table)

    raw = Prompt.ask("Select route (number)")
    try:
        idx = int(raw.strip()) - 1
        if 0 <= idx < len(existing):
            route_id = existing[idx]
            return route_id, _load_json(
                os.path.join(ROUTES_DIR, f"{route_id}.json")
            )
    except (ValueError, FileNotFoundError):
        pass
    console.print("[red]Invalid selection.[/red]")
    return None


def _add_segments_to_route() -> None:
    """Add road segments (and their halts) to an existing route."""
    console.print(Panel("[bold]Add Segments to Route[/bold]", expand=False))

    result = _select_route()
    if result is None:
        return
    route_id, route_data = result

    current_segs: list[str] = route_data.get("road_segment_id_list", [])
    console.print(
        f"\n[bold]Route:[/bold] [cyan]{route_id}[/cyan] — "
        f"{len(current_segs)} segment(s) currently"
    )
    for s in current_segs:
        console.print(f"  [dim]·[/dim] {s}")

    console.print("\n[bold]Add new road segments:[/bold]")
    while True:
        seg_id = _select_or_create_road_segment()
        if seg_id in current_segs:
            console.print(
                f"  [yellow]Segment [bold]{seg_id}[/bold] already in route — skipped.[/yellow]"
            )
        else:
            current_segs.append(seg_id)
            console.print(
                f"  [green]✓[/green] Added segment [bold]{seg_id}[/bold]"
            )

        more = Prompt.ask("\nAdd another road segment? [Y/n]", default="Y")
        if more.strip().lower() == "n":
            break

    route_data["road_segment_id_list"] = current_segs
    _save_json(os.path.join(ROUTES_DIR, f"{route_id}.json"), route_data)

    console.print(
        Panel(
            f"[bold green]Route [cyan]{route_id}[/cyan] now has "
            f"{len(current_segs)} segment(s).[/bold green]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# Update halt latlng
# ---------------------------------------------------------------------------


def _update_halt_latlng() -> None:
    """Select a road, then update latlng for halts on that road."""
    console.print(Panel("[bold]Update Halt LatLng[/bold]", expand=False))

    # --- pick a road ---
    roads = _list_db_ids(ROADS_DIR)
    if not roads:
        console.print("[yellow]No roads in DB yet.[/yellow]")
        return

    road_table = Table(title="Roads in DB", show_header=True, header_style="bold cyan")
    road_table.add_column("#", style="cyan", width=4)
    road_table.add_column("Road ID")
    for i, rid in enumerate(roads, 1):
        road_table.add_row(str(i), rid)
    console.print(road_table)

    raw = Prompt.ask("Select road (number)").strip()
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(roads)):
            raise ValueError
        road_id = roads[idx]
    except ValueError:
        console.print("[red]Invalid selection.[/red]")
        return

    # --- loop over halts on that road ---
    while True:
        all_halts = _list_db_ids(HALTS_DIR)
        road_halts = [h for h in all_halts if h.startswith(road_id + "-")]
        if not road_halts:
            console.print(f"[yellow]No halts found for road [bold]{road_id}[/bold].[/yellow]")
            return

        halt_table = Table(
            title=f"Halts on {road_id}", show_header=True, header_style="bold cyan"
        )
        halt_table.add_column("#", style="cyan", width=4)
        halt_table.add_column("Halt ID")
        halt_table.add_column("LatLng", style="dim")
        for i, hid in enumerate(road_halts, 1):
            try:
                data = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
                ll = data.get("latlng", {})
                latlng_str = f"{ll.get('lat', '?')}, {ll.get('lng', '?')}"
            except (FileNotFoundError, KeyError):
                latlng_str = ""
            halt_table.add_row(str(i), hid, latlng_str)
        console.print(halt_table)

        raw = Prompt.ask("Select halt (number, or [bold]done[/bold])", default="done").strip()
        if raw.lower() == "done":
            break
        try:
            hidx = int(raw) - 1
            if not (0 <= hidx < len(road_halts)):
                raise ValueError
        except ValueError:
            console.print("[red]Invalid selection.[/red]")
            continue

        halt_id = road_halts[hidx]
        halt_path = os.path.join(HALTS_DIR, f"{halt_id}.json")
        halt_data = _load_json(halt_path)

        while True:
            entry = Prompt.ask(f"  New LatLng for [cyan]{halt_id}[/cyan] (lat, lng)").strip()
            parts = entry.split(",")
            if len(parts) == 2:
                try:
                    lat, lng = float(parts[0].strip()), float(parts[1].strip())
                    break
                except ValueError:
                    pass
            console.print("[red]Enter as two numbers separated by a comma, e.g. 6.9171, 79.8656[/red]")

        halt_data["latlng"] = {"lat": lat, "lng": lng}
        _save_json(halt_path, halt_data)


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------


def main() -> None:
    _ensure_dirs()
    console.print(
        Panel("[bold blue]Bus Route Data Entry[/bold blue]", expand=False)
    )

    _ACTIONS = {
        "route": ("New Route", _new_route),
        "add": ("Add Segments to Route", _add_segments_to_route),
        "halt": ("Update Halt LatLng", _update_halt_latlng),
        "quit": ("Quit", None),
    }

    while True:
        console.print()
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Command", style="bold yellow", width=8)
        table.add_column("Action")
        for cmd, (desc, _) in _ACTIONS.items():
            table.add_row(cmd, desc)
        console.print(table)

        raw = Prompt.ask("Command", default="route").strip().lower()
        if raw not in _ACTIONS:
            console.print(
                f"[red]Unknown command '{raw}'. Try: {', '.join(_ACTIONS)}[/red]"
            )
            continue
        if raw == "quit":
            console.print("[dim]Bye.[/dim]")
            break
        _ACTIONS[raw][1]()


if __name__ == "__main__":
    main()
