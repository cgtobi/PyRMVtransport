"""Constants."""
from typing import List, Dict


PRODUCTS: Dict[str, int] = {
    "ICE": 1,
    "IC": 2,
    "EC": 2,
    "R": 4,
    "RB": 4,
    "RE": 4,
    "S": 8,
    "U-Bahn": 16,
    "Tram": 32,
    "Bus": 64,
    "Bus2": 128,
    "Fähre": 256,
    "Taxi": 512,
    "Bahn": 1024,
}

ALL_PRODUCTS: List[str] = list(PRODUCTS.keys())

MAX_RETRIES = 5

KNOWN_XML_ISSUES = {"<Arr getIn=false>": "<Arr >"}
