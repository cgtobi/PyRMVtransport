"""A module to query bus and train departure times."""
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime
import json
import logging
from typing import List, Dict, Any, Optional, Union
import aiohttp
import async_timeout
from lxml import objectify, etree  # type: ignore

from .errors import RMVtransportError, RMVtransportApiConnectionError
from .rmvjourney import RMVJourney
from .const import PRODUCTS, ALL_PRODUCTS, MAX_RETRIES, KNOWN_XML_ISSUES

_LOGGER = logging.getLogger(__name__)

BASE_URI: str = "http://www.rmv.de/auskunft/bin/jp/"
QUERY_PATH: str = "query.exe/"
GETSTOP_PATH: str = "ajax-getstop.exe/"
STBOARD_PATH: str = "stboard.exe/"


class RMVtransport:
    """Connection data and travel information."""

    def __init__(self, session: aiohttp.ClientSession, timeout: int = 10) -> None:
        """Initialize connection data."""
        self._session: aiohttp.ClientSession = session
        self._timeout: int = timeout

        self.now: datetime

        self.station: str
        self.station_id: str
        self.direction_id: Optional[str]
        self.products_filter: str

        self.max_journeys: int

        self.obj: objectify.ObjectifiedElement  # pylint: disable=I1101
        self.journeys: List[RMVJourney] = []

    async def get_departures(
        self,
        station_id: str,
        direction_id: Optional[str] = None,
        max_journeys: int = 20,
        products: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch data from rmv.de."""
        self.station_id = station_id
        self.direction_id = direction_id

        self.max_journeys = max_journeys

        self.products_filter = _product_filter(products or ALL_PRODUCTS)

        base_url: str = _base_url()
        params: Dict[str, Union[str, int]] = {
            "selectDate": "today",
            "time": "now",
            "input": self.station_id,
            "maxJourneys": self.max_journeys,
            "boardType": "dep",
            "productsFilter": self.products_filter,
            "disableEquivs": "discard_nearby",
            "output": "xml",
            "start": "yes",
        }
        if self.direction_id:
            params["dirInput"] = self.direction_id

        url = base_url + urllib.parse.urlencode(params)

        xml = await self._query_rmv_api(url)

        # pylint: disable=I1101
        retry = 0
        while retry < MAX_RETRIES:
            try:
                self.obj = objectify.fromstring(xml)
                break
            except (TypeError, etree.XMLSyntaxError) as e:
                _LOGGER.debug(f"Exception: {e}")
                xml_issue = xml.decode().split("\n")[e.lineno - 1]  # type: ignore
                _LOGGER.debug(xml_issue)
                _LOGGER.debug(f"Trying to fix the xml")
                if xml_issue in KNOWN_XML_ISSUES.keys():
                    xml = (
                        xml.decode()
                        .replace(
                            xml.decode().split("\n")[e.lineno - 1],  # type: ignore
                            KNOWN_XML_ISSUES[xml_issue],
                        )
                        .encode()
                    )
                    _LOGGER.debug(
                        xml.decode().split("\n")[e.lineno - 1]  # type: ignore
                    )
                else:
                    raise RMVtransportError()
                retry -= 1

        try:
            self.now = self.current_time()
            self.station = self._station()
        except (TypeError, AttributeError, ValueError) as e:
            _LOGGER.debug(
                f"Time/Station TypeError or AttributeError {e} "
                f"{objectify.dump(self.obj)[:100]}"
            )
            raise RMVtransportError()

        self.journeys.clear()
        try:
            for journey in self.obj.SBRes.JourneyList.Journey:
                self.journeys.append(RMVJourney(journey, self.now))
        except AttributeError:
            _LOGGER.debug(f"Extract journeys: {objectify.dump(self.obj.SBRes)}")
            raise RMVtransportError()

        return self.data()

    async def search_station(self, name: str, max_results: int = 25) -> Dict[str, Dict]:
        """Search station/stop my name."""
        base_url: str = _base_url(GETSTOP_PATH)

        params: Dict[str, Union[str, int]] = {
            "getstop": 1,
            "REQ0JourneyStopsS0A": max_results,
            "REQ0JourneyStopsS0G": name,
        }

        url = base_url + urllib.parse.urlencode(params)
        _LOGGER.debug(f"URL: {url}")

        res = await self._query_rmv_api(url)
        data = res.decode("utf-8")

        try:
            json_data = json.loads(
                data[data.find("{") : data.rfind("}") + 1]  # noqa: E203
            )
        except (TypeError, json.JSONDecodeError):
            _LOGGER.debug(f"Error in JSON: {data[:100]}...")
            raise RMVtransportError()

        suggestions = json_data["suggestions"][:max_results]

        return {
            item["extId"]: {
                "id": item["extId"],
                "name": item["value"],
                "lat": convert_coordinates(item["ycoord"]),
                "long": convert_coordinates(item["xcoord"]),
            }
            for item in suggestions
        }

    async def _query_rmv_api(self, url: str) -> bytes:
        """Query RMV API."""
        try:
            with async_timeout.timeout(self._timeout):
                async with self._session.get(url) as response:
                    _LOGGER.debug(f"Response from RMV API: {response.status}")
                    return await response.read()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load data from RMV API")
            raise RMVtransportApiConnectionError()

    def data(self) -> Dict[str, Any]:
        """Return travel data."""
        data: Dict[str, Any] = {}
        data["station"] = self.station
        data["stationId"] = self.station_id
        data["filter"] = self.products_filter

        journeys = []
        for j in sorted(self.journeys, key=lambda k: k.real_departure)[
            : self.max_journeys
        ]:
            journeys.append(
                {
                    "product": j.product,
                    "number": j.number,
                    "trainId": j.train_id,
                    "direction": j.direction,
                    "departure_time": j.real_departure_time,
                    "minutes": j.real_departure,
                    "delay": j.delay,
                    "stops": [s["station"] for s in j.stops],
                    "info": j.info,
                    "info_long": j.info_long,
                    "icon": j.icon,
                }
            )
        data["journeys"] = journeys
        return data

    def _station(self) -> str:
        """Extract station name."""
        return str(self.obj.SBRes.SBReq.Start.Station.HafasName.Text.pyval)

    def current_time(self) -> datetime:
        """Extract current time."""
        _date = datetime.strptime(self.obj.SBRes.SBReq.StartT.get("date"), "%Y%m%d")
        _time = datetime.strptime(self.obj.SBRes.SBReq.StartT.get("time"), "%H:%M")
        return datetime.combine(_date.date(), _time.time())

    def output(self) -> None:
        """Pretty print travel times."""
        print("%s - %s" % (self.station, self.now))
        print(self.products_filter)

        for j in sorted(self.journeys, key=lambda k: k.real_departure)[
            : self.max_journeys
        ]:
            print("-------------")
            print(f"{j.product}: {j.number} ({j.train_id})")
            print(f"Richtung: {j.direction}")
            print(f"Abfahrt in {j.real_departure} min.")
            print(f"Abfahrt {j.departure.time()} (+{j.delay})")
            print(f"Nächste Haltestellen: {([s['station'] for s in j.stops])}")
            if j.info:
                print(f"Hinweis: {j.info}")
                print(f"Hinweis (lang): {j.info_long}")
            print(f"Icon: {j.icon}")


def _product_filter(products) -> str:
    """Calculate the product filter."""
    _filter = 0
    for product in {PRODUCTS[p] for p in products}:
        _filter += product
    return format(_filter, "b")[::-1]


def _base_url(path: str = STBOARD_PATH) -> str:
    """Build base url."""
    _lang: str = "d"
    _type: str = "n"
    _with_suggestions: str = "?"
    return BASE_URI + path + _lang + _type + _with_suggestions


def convert_coordinates(value: str) -> float:
    """Convert coordinates to lat/long."""
    if len(value) < 8:
        return float(value[0] + "." + value[1:])
    return float(value[0:2] + "." + value[2:])
