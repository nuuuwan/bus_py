import sys
from utils import Log

from bus.core.Halt import Halt

log = Log("add_halt")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        log.error("Usage: python workflows/add_halt.py <google_maps_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    Halt.add_from_url(url)
