"""Define tests for the client object."""
import json
import httpx

import pytest

from RMVtransport import RMVtransport
from RMVtransport.rmvtransport import RMVtransportError

from .common import date_hook, URL, URL_SEARCH_PATH


@pytest.mark.asyncio
async def test_getdepartures(httpx_mock, xml_request, capsys):
    """Test departures with default setings."""
    with open("fixtures/result_simple.json") as f:
        result_simple_json = json.load(f, object_hook=date_hook)
    with open("fixtures/result_simple.txt") as f:
        result_text = f.read()

    httpx_mock.add_response(data=xml_request)

    rmv = RMVtransport()

    station_id = "3006904"
    data = await rmv.get_departures(station_id)

    assert data == result_simple_json

    rmv.print()
    out, err = capsys.readouterr()
    assert out == result_text
    assert err == ""


@pytest.mark.asyncio
async def test_departures_products(httpx_mock, xml_request):
    """Test products filter."""
    with open("fixtures/result_products_filter.json") as f:
        result_products_filter_json = json.load(f, object_hook=date_hook)

    httpx_mock.add_response(data=xml_request)

    rmv = RMVtransport()

    station_id = "3006904"
    products = ["S", "RB"]
    data = await rmv.get_departures(station_id, products=products, max_journeys=50)
    assert data == result_products_filter_json


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_departures_error_xml(httpx_mock):
    """Test with bad xml."""
    httpx_mock.add_response(data="<ResC></ResC>")

    rmv = RMVtransport()

    station_id = "3006904"
    await rmv.get_departures(station_id)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_no_xml(httpx_mock):
    """Test with empty xml."""
    httpx_mock.add_response(data="")

    rmv = RMVtransport()

    station_id = "3006904"
    await rmv.get_departures(station_id)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_departures_error_server(httpx_mock):
    """Test server error handling."""
    httpx_mock.add_response(data="error", status_code=500)

    rmv = RMVtransport()

    station_id = "3006904"
    await rmv.get_departures(station_id)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=TypeError)
async def test_no_station_id():
    """Test no station_id error handling."""
    rmv = RMVtransport()
    await rmv.get_departures()


@pytest.mark.asyncio
async def test_departures_bad_request(httpx_mock):
    """Test bad xml."""
    with open("fixtures/bad_request.xml") as xml_file:
        xml_request = xml_file.read()
    with open("fixtures/result_bad.json") as json_file:
        result = json.load(json_file, object_hook=date_hook)

    httpx_mock.add_response(data=xml_request)

    rmv = RMVtransport()

    station_id = "3006904"
    direction_id = "3006905"
    data = await rmv.get_departures(station_id, direction_id)
    assert data == result


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_no_journeys(httpx_mock):
    """Test with no journeys."""
    with open("fixtures/request_no_journeys.xml") as f:
        xml = f.read()

    httpx_mock.add_response(data=xml)

    rmv = RMVtransport()

    station_id = "3006904"
    await rmv.get_departures(station_id)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_no_timestamp(httpx_mock):
    """Test with no timestamp."""
    with open("fixtures/request_no_timestamp.xml") as f:
        xml = f.read()

    httpx_mock.add_response(data=xml)

    rmv = RMVtransport()

    station_id = "3006904"
    await rmv.get_departures(station_id)


@pytest.mark.asyncio
async def test_midnight(httpx_mock):
    """Test departures around midnight."""
    with open("fixtures/request_midnight.xml") as f:
        xml = f.read()
    with open("fixtures/result_midnight.json") as f:
        result = json.load(f, object_hook=date_hook)

    httpx_mock.add_response(data=xml)

    rmv = RMVtransport()

    station_id = "3006904"
    data = await rmv.get_departures(station_id)
    assert data == result


@pytest.mark.asyncio
async def test_search_station(httpx_mock, stops_request):
    """Test station search."""
    httpx_mock.add_response(data=stops_request)

    rmv = RMVtransport()

    station = "Hauptwache"
    data = await rmv.search_station(station)
    assert data == {
        "003000001": {
            "name": "Frankfurt (Main) Hauptwache",
            "id": "003000001",
            "lat": 50.113963,
            "long": 8.679292,
        }
    }


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_search_station_fail(httpx_mock):
    """Test failing station search."""
    with open("fixtures/request_no_timestamp.xml") as f:
        xml = f.read()

    httpx_mock.add_response(data=xml)

    rmv = RMVtransport()

    station = "Hauptwache"
    data = await rmv.search_station(station)
    assert data == {
        "003000001": {
            "name": "Frankfurt (Main) Hauptwache",
            "id": "003000001",
            "lat": 50.113963,
            "long": 8.679292,
        }
    }


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test__query_rmv_api_fail(httpx_mock):
    """Test failing station search."""

    def raise_timeout(request, ext: dict):
        raise httpx.ReadTimeout(
            f"Unable to read within {ext['timeout']}", request=request
        )

    httpx_mock.add_callback(raise_timeout)

    with pytest.raises(httpx.ReadTimeout):
        rmv = RMVtransport(timeout=0.005)

        url = f"https://{URL}{URL_SEARCH_PATH}"
        await rmv._query_rmv_api(url)
