#!/usr/bin/env python3
"""Console workflow for adding bus route data."""

import json
import os
import subprocess
import sys

import contextily as ctx
import matplotlib.pyplot as plt

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


def _validate_halt_latlng(
    latlng: LatLng, road_id: str, road_index: int
) -> list[str]:
    """Return a list of validation error messages (empty list = valid)."""
    errors = []
    all_halt_ids = _list_db_ids(HALTS_DIR)

    # Rule 1: at least 1 m from every existing halt
    for hid in all_halt_ids:
        try:
            hdata = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
            ll = hdata.get("latlng", {})
            other = LatLng(lat=ll["lat"], lng=ll["lng"])
            dist = latlng.distance_m(other)
            if dist < 1.0:
                errors.append(
                    f"Too close to [bold]{hid}[/bold] ({dist:.2f} m — must be ≥ 1 m)"
                )
        except (FileNotFoundError, KeyError):
            continue

    # Rule 2: no more than 1 km from the immediately preceding halt on the same road
    prev_halts: list[tuple[int, LatLng, str]] = []
    for hid in all_halt_ids:
        if not hid.startswith(road_id + "-"):
            continue
        try:
            hdata = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
            ridx = hdata.get("road_index", 0)
            if ridx < road_index:
                ll = hdata.get("latlng", {})
                prev_halts.append(
                    (ridx, LatLng(lat=ll["lat"], lng=ll["lng"]), hid)
                )
        except (FileNotFoundError, KeyError):
            continue

    if prev_halts:
        prev_halts.sort(key=lambda h: h[0])
        _, prev_latlng, prev_hid = prev_halts[-1]
        dist = latlng.distance_m(prev_latlng)
        if dist > 1_000.0:
            errors.append(
                f"Too far from previous halt [bold]{prev_hid}[/bold] "
                f"({dist:.0f} m — must be ≤ 1 km)"
            )

    return errors


def _geocode(
    halt_name: str,
    road_name: str,
    road_id: str | None = None,
    road_index: int | None = None,
) -> LatLng:
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
                if road_id is not None and road_index is not None:
                    errs = _validate_halt_latlng(latlng, road_id, road_index)
                    if errs:
                        for e in errs:
                            console.print(f"  [red]{e}[/red]")
                        continue
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
            "Road (number to select, or [bold]N[/bold]ew)", default="N"
        )
        if raw.strip().upper() != "N":
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

    _VALID_DIRECTIONS = {"N", "S", "E", "W"}
    direction = ""
    while direction not in _VALID_DIRECTIONS:
        direction = Prompt.ask("Road Direction [N|S|E|W]").strip().upper()
        if direction not in _VALID_DIRECTIONS:
            console.print("[red]Must be one of N, S, E, W.[/red]")

    road = Road(name=road_name, direction=direction)
    road_id = road.id

    _save_json(
        os.path.join(ROADS_DIR, f"{road_id}.json"),
        {"name": road_name, "direction": direction},
    )

    # Collect halts
    console.print(
        f"\n[bold]Add halts for [cyan]{road_name}[/cyan] (leave blank to stop):[/bold]"
    )

    def _next_road_index() -> int:
        """Highest road_index currently on this road + 1, or 0 if none."""
        ids = _list_db_ids(HALTS_DIR)
        indices = []
        for hid in ids:
            if not hid.startswith(road_id + "-"):
                continue
            try:
                d = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
                indices.append(d.get("road_index", 0))
            except (FileNotFoundError, KeyError):
                pass
        return max(indices) + 1 if indices else 0

    halt_counter = 0
    while True:
        halt_name = Prompt.ask(
            f"  Halt name (leave blank to stop)", default=""
        )
        if not halt_name.strip():
            break

        # Duplicate check
        existing_halt_ids = _list_db_ids(HALTS_DIR)
        candidate_id = f"{road_id}-{String.to_kebab_case(halt_name.strip())}"
        if candidate_id in existing_halt_ids:
            console.print(
                f"  [red]Halt '[bold]{halt_name.strip()}[/bold]' already exists on this road — skipped.[/red]"
            )
            continue

        # Ask insert position
        end_index = _next_road_index()
        pos_raw = (
            Prompt.ask(
                f"  Position — insert [bold]after[/bold] index (number) or [bold]E[/bold]nd (index {end_index})",
                default="E",
            )
            .strip()
            .upper()
        )

        if pos_raw == "E":
            road_index = end_index
        else:
            try:
                after = int(pos_raw)
                road_index = after + 1
            except ValueError:
                console.print(
                    "[red]Invalid position — appending at end.[/red]"
                )
                road_index = end_index

        # Shift existing halts with road_index >= road_index
        if road_index < end_index:
            ids_on_road = sorted(
                [
                    hid
                    for hid in _list_db_ids(HALTS_DIR)
                    if hid.startswith(road_id + "-")
                ]
            )
            for hid in reversed(ids_on_road):
                try:
                    hdata = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
                    if hdata.get("road_index", 0) >= road_index:
                        hdata["road_index"] += 1
                        _save_json(
                            os.path.join(HALTS_DIR, f"{hid}.json"), hdata
                        )
                except (FileNotFoundError, KeyError):
                    pass
            # Shift road segments on this road
            for sid in _list_db_ids(ROAD_SEGMENTS_DIR):
                seg_path = os.path.join(ROAD_SEGMENTS_DIR, f"{sid}.json")
                try:
                    seg = _load_json(seg_path)
                except FileNotFoundError:
                    continue
                if seg.get("road_id") != road_id:
                    continue
                changed = False
                if seg.get("start_road_index", 0) >= road_index:
                    seg["start_road_index"] += 1
                    changed = True
                if seg.get("end_road_index", 0) >= road_index:
                    seg["end_road_index"] += 1
                    changed = True
                if changed:
                    new_seg_id = RoadSegment(
                        road_id=road_id,
                        start_road_index=seg["start_road_index"],
                        end_road_index=seg["end_road_index"],
                    ).id
                    os.replace(
                        seg_path,
                        os.path.join(ROAD_SEGMENTS_DIR, f"{new_seg_id}.json"),
                    )
                    for rid in _list_db_ids(ROUTES_DIR):
                        route_path = os.path.join(ROUTES_DIR, f"{rid}.json")
                        try:
                            rdata = _load_json(route_path)
                            seg_list = rdata.get("road_segment_id_list", [])
                            if sid in seg_list:
                                seg_list[seg_list.index(sid)] = new_seg_id
                                rdata["road_segment_id_list"] = seg_list
                                _save_json(route_path, rdata)
                        except (FileNotFoundError, KeyError):
                            continue
                    _save_json(
                        os.path.join(ROAD_SEGMENTS_DIR, f"{new_seg_id}.json"),
                        seg,
                    )

        latlng = _geocode(
            halt_name.strip(),
            road_name,
            road_id=road_id,
            road_index=road_index,
        )
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
        halt_counter += 1

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
            "RoadSegment (number to select, or [bold]N[/bold]ew)",
            default="N",
        )
        if raw.strip().upper() != "N":
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

    road_table = Table(
        title="Roads in DB", show_header=True, header_style="bold cyan"
    )
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
            console.print(
                f"[yellow]No halts found for road [bold]{road_id}[/bold].[/yellow]"
            )
            return

        halt_table = Table(
            title=f"Halts on {road_id}",
            show_header=True,
            header_style="bold cyan",
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

        raw = Prompt.ask(
            "Select halt (number, or [bold]D[/bold]one)", default="D"
        ).strip()
        if raw.upper() == "D":
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
            entry = Prompt.ask(
                f"  New LatLng for [cyan]{halt_id}[/cyan] (lat, lng)"
            ).strip()
            parts = entry.split(",")
            if len(parts) == 2:
                try:
                    lat, lng = float(parts[0].strip()), float(parts[1].strip())
                    break
                except ValueError:
                    pass
            console.print(
                "[red]Enter as two numbers separated by a comma, e.g. 6.9171, 79.8656[/red]"
            )

        halt_data["latlng"] = {"lat": lat, "lng": lng}
        _save_json(halt_path, halt_data)


# ---------------------------------------------------------------------------
# Render route map
# ---------------------------------------------------------------------------


def _render_route_map() -> None:
    """Render a matplotlib map for a selected route showing all its halts."""
    console.print(Panel("[bold]Render Route Map[/bold]", expand=False))

    result = _select_route()
    if result is None:
        return
    route_id, route_data = result

    seg_ids: list[str] = route_data.get("road_segment_id_list", [])

    # Load segment metadata
    segments: list[dict] = []
    for sid in seg_ids:
        seg_path = os.path.join(ROAD_SEGMENTS_DIR, f"{sid}.json")
        try:
            segments.append(_load_json(seg_path))
        except FileNotFoundError:
            console.print(f"  [yellow]Segment file not found: {sid}[/yellow]")

    all_halt_ids = _list_db_ids(HALTS_DIR)

    # Build ordered list of halts per segment, sorted by road_index
    # Each entry: (lat, lng, label)
    segments_halts: list[list[tuple[float, float, str]]] = []

    for seg in segments:
        road_id = seg["road_id"]
        start_idx = seg.get("start_road_index", 0)
        end_idx = seg.get("end_road_index", 9999)

        seg_halts: list[tuple[int, float, float, str]] = (
            []
        )  # (road_index, lat, lng, label)
        for hid in all_halt_ids:
            if not hid.startswith(road_id + "-"):
                continue
            try:
                hdata = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
                ridx = hdata.get("road_index", 0)
                if start_idx <= ridx <= end_idx:
                    ll = hdata.get("latlng", {})
                    lat = ll.get("lat")
                    lng = ll.get("lng")
                    if lat is not None and lng is not None:
                        label = f"{road_id} [{ridx}]\n{hdata.get('name', hid)}"
                        seg_halts.append((ridx, lat, lng, label))
            except (FileNotFoundError, KeyError):
                continue

        seg_halts.sort(key=lambda h: h[0])
        segments_halts.append(
            [(lat, lng, label) for _, lat, lng, label in seg_halts]
        )

    # Flatten to ordered halt_points and record segment boundaries for linking
    halt_points: list[tuple[float, float, str]] = []
    for seg_h in segments_halts:
        halt_points.extend(seg_h)

    if not halt_points:
        console.print(
            "[yellow]No halts with latlng found for this route.[/yellow]"
        )
        return

    console.print(f"  Plotting [bold]{len(halt_points)}[/bold] halt(s)…")

    try:
        import matplotlib

        matplotlib.use("TkAgg")
    except Exception:
        pass

    fig, ax = plt.subplots(figsize=(8, 10))

    lats = [p[0] for p in halt_points]
    lngs = [p[1] for p in halt_points]

    try:
        import pyproj

        transformer = pyproj.Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        )
        xs, ys = transformer.transform(lngs, lats)
    except Exception:
        xs, ys = lngs, lats
        transformer = None

    # Draw lines segment by segment (last of one links to first of next)
    offset = 0
    for seg_h in segments_halts:
        n = len(seg_h)
        if n == 0:
            continue
        seg_xs = xs[offset : offset + n]
        seg_ys = ys[offset : offset + n]
        ax.plot(seg_xs, seg_ys, color="steelblue", linewidth=1.5, zorder=4)
        # Link last halt of this segment to first halt of next segment
        if offset + n < len(halt_points):
            ax.plot(
                [xs[offset + n - 1], xs[offset + n]],
                [ys[offset + n - 1], ys[offset + n]],
                color="steelblue",
                linewidth=1.5,
                linestyle="dashed",
                zorder=4,
            )
        offset += n

    ax.scatter(xs, ys, zorder=5, color="crimson", s=60)
    for x, y, label in zip(xs, ys, [p[2] for p in halt_points]):
        ax.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=6,
            zorder=6,
        )

    if transformer is not None:
        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
        except Exception as exc:
            console.print(f"  [yellow]Basemap unavailable: {exc}[/yellow]")

    ax.set_title(f"Route {route_data.get('code', route_id)} — {route_id}")
    ax.set_axis_off()
    plt.tight_layout()

    img_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "images",
            "routes",
            f"{route_id}.png",
        )
    )
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    plt.savefig(img_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    console.print(f"  [green]Saved →[/green] {img_path}")

    # Open with the OS default image viewer
    subprocess.Popen(["open", img_path])

    console.print("[dim]Bye.[/dim]")
    raise SystemExit(0)


# ---------------------------------------------------------------------------
# Insert halt between two indexes on a road
# ---------------------------------------------------------------------------


def _insert_halt() -> None:
    """Insert a new halt at a given road_index, shifting later halts up by 1."""
    console.print(Panel("[bold]Insert Halt[/bold]", expand=False))

    # 1. Select road
    roads = _list_db_ids(ROADS_DIR)
    if not roads:
        console.print("[yellow]No roads in DB yet.[/yellow]")
        return

    road_table = Table(
        title="Roads in DB", show_header=True, header_style="bold cyan"
    )
    road_table.add_column("#", style="cyan", width=4)
    road_table.add_column("Road ID")
    for i, rid in enumerate(roads, 1):
        road_table.add_row(str(i), rid)
    console.print(road_table)

    raw = Prompt.ask("Select road (number)").strip()
    try:
        road_id = roads[int(raw) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        return

    # 2. Show current halts on the road sorted by road_index
    all_halt_ids = _list_db_ids(HALTS_DIR)
    road_halts: list[tuple[int, str, dict]] = []  # (road_index, halt_id, data)
    for hid in all_halt_ids:
        if not hid.startswith(road_id + "-"):
            continue
        try:
            hdata = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
            road_halts.append((hdata.get("road_index", 0), hid, hdata))
        except (FileNotFoundError, KeyError):
            continue
    road_halts.sort(key=lambda h: h[0])

    if not road_halts:
        console.print(
            f"[yellow]No halts on road [bold]{road_id}[/bold] yet.[/yellow]"
        )
        return

    halt_table = Table(
        title=f"Halts on {road_id}", show_header=True, header_style="bold cyan"
    )
    halt_table.add_column("Index", style="cyan", width=6)
    halt_table.add_column("Halt ID")
    for ridx, hid, _ in road_halts:
        halt_table.add_row(str(ridx), hid)
    console.print(halt_table)

    # 3. Ask for insert position
    raw = Prompt.ask(
        "Insert at road_index (new halt gets this index; later halts shift up)"
    ).strip()
    try:
        insert_at = int(raw)
    except ValueError:
        console.print("[red]Invalid index.[/red]")
        return

    # 4. Shift all halts with road_index >= insert_at
    for ridx, hid, hdata in reversed(road_halts):
        if ridx < insert_at:
            continue
        old_path = os.path.join(HALTS_DIR, f"{hid}.json")
        new_ridx = ridx + 1
        hdata["road_index"] = new_ridx
        # Rebuild halt id (road_id + kebab name, no index in id — just overwrite same file)
        _save_json(old_path, hdata)

    # 5. Update road segments whose end_road_index >= insert_at for this road
    for sid in _list_db_ids(ROAD_SEGMENTS_DIR):
        seg_path = os.path.join(ROAD_SEGMENTS_DIR, f"{sid}.json")
        try:
            seg = _load_json(seg_path)
        except FileNotFoundError:
            continue
        if seg.get("road_id") != road_id:
            continue
        changed = False
        if seg.get("start_road_index", 0) >= insert_at:
            seg["start_road_index"] += 1
            changed = True
        if seg.get("end_road_index", 0) >= insert_at:
            seg["end_road_index"] += 1
            changed = True
        if changed:
            # Rename segment file to reflect new indices
            new_seg_id = RoadSegment(
                road_id=road_id,
                start_road_index=seg["start_road_index"],
                end_road_index=seg["end_road_index"],
            ).id
            os.replace(
                seg_path, os.path.join(ROAD_SEGMENTS_DIR, f"{new_seg_id}.json")
            )
            # Update routes that referenced old segment id
            for rid in _list_db_ids(ROUTES_DIR):
                route_path = os.path.join(ROUTES_DIR, f"{rid}.json")
                try:
                    rdata = _load_json(route_path)
                    seg_list = rdata.get("road_segment_id_list", [])
                    if sid in seg_list:
                        seg_list[seg_list.index(sid)] = new_seg_id
                        rdata["road_segment_id_list"] = seg_list
                        _save_json(route_path, rdata)
                except (FileNotFoundError, KeyError):
                    continue
            _save_json(
                os.path.join(ROAD_SEGMENTS_DIR, f"{new_seg_id}.json"), seg
            )

    # 6. Prompt for new halt
    road_data = _load_json(os.path.join(ROADS_DIR, f"{road_id}.json"))
    road_name = road_data.get("name", road_id)
    halt_name = Prompt.ask(f"  New halt name at index {insert_at}").strip()
    latlng = _geocode(
        halt_name, road_name, road_id=road_id, road_index=insert_at
    )
    halt = Halt(
        road_id=road_id,
        road_index=insert_at,
        name=halt_name,
        latlng=latlng,
    )
    _save_json(
        os.path.join(HALTS_DIR, f"{halt.id}.json"),
        {
            "road_id": road_id,
            "road_index": insert_at,
            "name": halt_name,
            "latlng": {"lat": latlng.lat, "lng": latlng.lng},
        },
    )
    console.print(
        Panel(
            f"[bold green]Inserted halt [cyan]{halt_name}[/cyan] at index {insert_at} on {road_id}.[/bold green]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# Validate DB
# ---------------------------------------------------------------------------


def _validate_db() -> None:
    """Check road index continuity and route ordering for all roads/routes."""
    console.print(Panel("[bold]Validate DB[/bold]", expand=False))
    ok = True

    # ------------------------------------------------------------------
    # 1. Road index continuity: road with N halts must have indices 0..N-1
    # ------------------------------------------------------------------
    console.print("\n[bold cyan]1. Road index continuity[/bold cyan]")
    all_halt_ids = _list_db_ids(HALTS_DIR)

    # Group halts by road_id
    road_to_halts: dict[str, list[tuple[int, str]]] = {}
    for hid in all_halt_ids:
        try:
            hdata = _load_json(os.path.join(HALTS_DIR, f"{hid}.json"))
            rid = hdata.get("road_id", "")
            ridx = hdata.get("road_index", -1)
            road_to_halts.setdefault(rid, []).append((ridx, hid))
        except (FileNotFoundError, KeyError):
            continue

    for rid, entries in sorted(road_to_halts.items()):
        indices = sorted(e[0] for e in entries)
        n = len(indices)
        expected = list(range(n))
        if indices != expected:
            ok = False
            missing = sorted(set(expected) - set(indices))
            extra = sorted(set(indices) - set(expected))
            parts = []
            if missing:
                parts.append(f"missing indices {missing}")
            if extra:
                parts.append(f"unexpected indices {extra}")
            console.print(
                f"  [red][bold]{rid}[/bold] — " + "; ".join(parts) + "[/red]"
            )
        else:
            console.print(f"  [green]✓[/green] {rid} ({n} halt(s))")

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    console.print()
    if ok:
        console.print(
            Panel("[bold green]All checks passed.[/bold green]", expand=False)
        )
    else:
        console.print(
            Panel(
                "[bold red]Anomalies found — see above.[/bold red]",
                expand=False,
            )
        )


def main() -> None:
    _ensure_dirs()
    console.print(
        Panel("[bold blue]Bus Route Data Entry[/bold blue]", expand=False)
    )

    _ACTIONS = {
        "R": ("New Route", _new_route),
        "A": ("Add Segments to Route", _add_segments_to_route),
        "H": ("Update Halt LatLng", _update_halt_latlng),
        "I": ("Insert Halt at Index", _insert_halt),
        "M": ("Render Route Map", _render_route_map),
        "V": ("Validate DB", _validate_db),
        "Q": ("Quit", None),
    }

    while True:
        console.print()
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Command", style="bold yellow", width=8)
        table.add_column("Action")
        for cmd, (desc, _) in _ACTIONS.items():
            table.add_row(cmd, desc)
        console.print(table)

        raw = Prompt.ask("Command", default="R").strip().upper()
        if raw not in _ACTIONS:
            console.print(
                f"[red]Unknown command '{raw}'. Try: {', '.join(_ACTIONS)}[/red]"
            )
            continue
        if raw == "Q":
            console.print("[dim]Bye.[/dim]")
            break
        _ACTIONS[raw][1]()


if __name__ == "__main__":
    main()
