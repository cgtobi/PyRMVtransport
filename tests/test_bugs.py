"""Define tests for the client object."""
from datetime import datetime
import logging

import pytest

from RMVtransport import RMVtransport


logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

URL = "www.rmv.de"
URL_PATH = "/auskunft/bin/jp/stboard.exe/dn"
URL_SEARCH_PATH = "/auskunft/bin/jp/ajax-getstop.exe/dn"


def date_hook(json_dict):
    """JSON datetime parser."""
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            pass
    return json_dict


@pytest.mark.asyncio
async def test_bug_3006907(httpx_mock, capsys):
    """Test bug 3006907."""
    with open("fixtures/bug_3006907.xml") as f:
        xml_request = f.read()

    httpx_mock.add_response(data=xml_request)

    rmv = RMVtransport()

    station_id = "3006907"
    data = await rmv.get_departures(
        station_id, max_journeys=50, products=["U-Bahn", "Tram", "Bus", "S"]
    )
    assert data["filter"] == "0001111"
    assert data["stationId"] == "3006907"
    assert data["station"] == "Wiesbaden Hauptbahnhof"
