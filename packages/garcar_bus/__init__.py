"""Garcar Event Mesh — shared bus for every system.

Install from hub:
  pip install git+https://github.com/Garrettc123/systems-master-hub.git#subdirectory=packages/garcar_bus

Or copy the package into any repo and:
  from garcar_bus import bus
  bus.publish("revenue.captured", {"amount": 47, "system": "NEXUS"})
  bus.subscribe("revenue.captured", handler)
"""

from .bus import Bus, bus

__all__ = ["Bus", "bus"]
__version__ = "0.1.0"
