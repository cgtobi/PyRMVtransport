"""Define tests for the client object."""
from datetime import datetime
import json
import aiohttp

from asynctest import MagicMock, patch, CoroutineMock

import pytest
import pytest_asyncio.plugin

import aresponses

from RMVtransport import RMVtransport
from RMVtransport.rmvtransport import RMVtransportError


URL = 'www.rmv.de'
URL_PATH = ('/auskunft/bin/jp/stboard.exe/dn')


def date_hook(json_dict):
    """JSON datetime parser."""
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            pass
    return json_dict


@pytest.fixture
def xml_request():
    with open('fixtures/request.xml') as f:
        return f.read()


@pytest.mark.asyncio
async def test_getdepartures(event_loop, xml_request, capsys):
    """Test departures with default setings."""
    with open('fixtures/result_simple.json') as f:
        result_simple_json = json.load(f, object_hook=date_hook)
    with open('fixtures/result_simple.txt') as f:
        result_text = f.read()
    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', xml_request)

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            data = await rmv.get_departures(stationId)
            assert data == result_simple_json

            rmv.output()
            out, err = capsys.readouterr()
            assert out == result_text


@pytest.mark.asyncio
async def test_departures_products(event_loop, xml_request):
    """Test products filter."""
    with open('fixtures/result_products_filter.json') as f:
        result_products_filter_json = json.load(f, object_hook=date_hook)
    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', xml_request)

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            products = ['S', 'RB']
            data = await rmv.get_departures(stationId,
                                            products=products,
                                            max_journeys=50)
            assert data == result_products_filter_json


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_departures_error_xml(event_loop):
    """Test with bad xml."""
    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', '<ResC></ResC>')

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            await rmv.get_departures(stationId)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_no_xml(event_loop):
    """Test with empty xml."""
    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', '')

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            await rmv.get_departures(stationId)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_departures_error_server(event_loop):
    """Test server error handling."""
    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', aresponses.Response(text='error',
                                                            status=500))

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            await rmv.get_departures(stationId)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=TypeError)
async def test_no_station_id(event_loop):
    """Test no station_id error handling."""
    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', aresponses.Response(text='error',
                                                            status=500))

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)
            await rmv.get_departures()


@pytest.mark.asyncio
async def test_departures_bad_request(event_loop):
    """Test bad xml."""
    with open('fixtures/bad_request.xml') as xml_file:
        xml_request = xml_file.read()
    with open('fixtures/result_bad.json') as json_file:
        result = json.load(json_file, object_hook=date_hook)

    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', xml_request)

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            directionId = '3006905'
            data = await rmv.get_departures(stationId, directionId)
            assert data == result


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_no_journeys(event_loop):
    """Test with no journeys."""
    with open('fixtures/request_no_journeys.xml') as f:
        xml = f.read()

    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', xml)

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            await rmv.get_departures(stationId)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RMVtransportError)
async def test_no_timestamp(event_loop):
    """Test with no timestamp."""
    with open('fixtures/request_no_timestamp.xml') as f:
        xml = f.read()

    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', xml)

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            await rmv.get_departures(stationId)


@pytest.mark.asyncio
async def test_midnight(event_loop):
    """Test departures around midnight."""
    with open('fixtures/request_midnight.xml') as f:
        xml = f.read()
    with open('fixtures/result_midnight.json') as f:
        result = json.load(f, object_hook=date_hook)

    async with aresponses.ResponsesMockServer(loop=event_loop) as arsps:
        arsps.add(URL, URL_PATH, 'get', xml)

        async with aiohttp.ClientSession(loop=event_loop) as session:
            rmv = RMVtransport(session)

            stationId = '3006904'
            data = await rmv.get_departures(stationId)
            assert data == result
