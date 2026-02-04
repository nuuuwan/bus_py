import sys

from bus.core.Halt import Halt

log = Log("add_halt")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        log.error("Usage: python workflows/add_halt.py <name> <lat> <lng>")
        sys.exit(1)
    
    name = sys.argv[1]
    lat = float(sys.argv[2].replace(',', ""))
    lng = float(sys.argv[3].replace(',', ""))
    
    Halt.add_new_halt(name, (lat, lng))
