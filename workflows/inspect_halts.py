import sys
import webbrowser

from utils import Log

from bus.core.Halt import Halt

log = Log("inspect_halts")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        log.error(
            "Usage: python workflows/inspect_halts.py <start_index> <end_index>"
        )
        sys.exit(1)

    start_index = int(sys.argv[1])
    end_index = int(sys.argv[2])
    halts = Halt.list_all()

    if start_index < 0 or end_index >= len(halts) or start_index > end_index:
        log.error(
            f"Invalid range: {start_index} to {end_index}. Total halts: {len(halts)}"
        )
        sys.exit(1)

    selected_halts = halts[start_index:end_index]

    log.info(
        f"Opening {len(selected_halts)} halts in Google Maps (indexes {start_index} to {end_index})"
    )

    for i, halt in enumerate(selected_halts, start=start_index):
        lat, lng = halt.latlng
        url = f"https://www.google.com/maps?q={lat},{lng}"
        log.info(f"[{i}] {halt.name}: {url}")
        webbrowser.open(url)
