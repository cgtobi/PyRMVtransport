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

MAX_RETRIES: int = 5

KNOWN_XML_ISSUES: Dict[str, str] = {"<Arr getIn=false>": "<Arr >"}

BASE_URI: str = "https://www.rmv.de/auskunft/"
PREFIX: str = "bin/jp/"
QUERY_PATH: str = PREFIX + "query.exe/"
GETSTOP_PATH: str = PREFIX + "ajax-getstop.exe/"
STBOARD_PATH: str = PREFIX + "stboard.exe/"
IMG_URL: str = BASE_URI + "s/n/img/products/%i_pic.png"
