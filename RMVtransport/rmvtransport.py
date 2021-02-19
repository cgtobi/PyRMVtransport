"""A module to query bus and train departure times."""
import asyncio
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import async_timeout
import httpx
from lxml import etree, objectify  # type: ignore

from .const import (
    ALL_PRODUCTS,
    BASE_URI,
    GETSTOP_PATH,
    KNOWN_XML_ISSUES,
    MAX_RETRIES,
    PRODUCTS,
    STBOARD_PATH,
)
from .errors import (
    RMVtransportApiConnectionError,
    RMVtransportDataError,
    RMVtransportError,
)
from .rmvjourney import RMVJourney

_LOGGER = logging.getLogger(__name__)


class RMVtransport:
    """Connection data and travel information."""

    def __init__(self, timeout: float = 10) -> None:
        """Initialize connection data."""
        self._timeout: float = timeout

        self.now: datetime

        self.station_id: str
        self.direction_id: Optional[str]
        self.products_filter: str

        self.max_journeys: int

        self.obj: objectify.ObjectifiedElement
        self.journeys: List[RMVJourney] = []

    async def get_departures(
        self,
        station_id: str,
        direction_id: Optional[str] = None,
        max_journeys: int = 20,
        products: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch data from rmv.de."""
        url = self.build_journey_query(station_id, direction_id, max_journeys, products)
        xml = await self._query_rmv_api(url)
        self.obj = extract_data_from_xml(xml)

        try:
            self.now = self.current_time()
        except RMVtransportDataError:
            _LOGGER.debug(
                "XML contains unexpected data %s", objectify.dump(self.obj)[:100]
            )
            raise

        self.journeys.clear()
        try:
            for journey in self.obj.SBRes.JourneyList.Journey:
                self.journeys.append(RMVJourney(journey, self.now))
        except AttributeError:
            _LOGGER.debug("Extract journeys: %s", objectify.dump(self.obj.SBRes))
            raise RMVtransportError()

        return self.travel_data()

    def build_journey_query(
        self,
        station_id: str,
        direction_id: Optional[str] = None,
        max_journeys: int = 20,
        products: Optional[List[str]] = None,
    ) -> str:
        """Build query to request journey data."""
        self.station_id = station_id
        self.direction_id = direction_id
        self.max_journeys = max_journeys
        self.products_filter = product_filter(products or ALL_PRODUCTS)

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

        return base_url() + urllib.parse.urlencode(params)

    async def search_station(self, name: str, max_results: int = 25) -> Dict[str, Dict]:
        """Search station/stop my name."""
        suggestions: List = await self._fetch_sugestions(name, max_results)

        return {
            item["extId"]: {
                "id": item["extId"],
                "name": item["value"],
                "lat": convert_coordinates(item["ycoord"]),
                "long": convert_coordinates(item["xcoord"]),
            }
            for item in suggestions
        }

    async def _fetch_sugestions(
        self, name: str, max_results: int
    ) -> List[Optional[Dict]]:
        """Fetch suggestsions for the given station name from the backend."""
        params: Dict[str, Union[str, int]] = {
            "getstop": 1,
            "REQ0JourneyStopsS0A": max_results,
            "REQ0JourneyStopsS0G": name,
        }

        url = base_url(GETSTOP_PATH) + urllib.parse.urlencode(params)
        _LOGGER.debug("URL: %s", url)

        response = await self._query_rmv_api(url)
        data = extract_json_data(response)

        try:
            json_data = json.loads(data)
        except (TypeError, json.JSONDecodeError):
            _LOGGER.debug("Error in JSON: %s...", data[:100])
            raise RMVtransportError()

        return list(json_data["suggestions"][:max_results])

    async def _query_rmv_api(self, url: str) -> Any:
        """Query RMV API."""
        with async_timeout.timeout(self._timeout):
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url)
                except (
                    asyncio.TimeoutError,
                    httpx.ReadTimeout,
                    httpx.ConnectTimeout,
                    httpx.ConnectError,
                ):
                    _LOGGER.error("Can not load data from RMV API")
                    raise RMVtransportApiConnectionError()

        _LOGGER.debug("Response from RMV API: %s", response.status_code)
        return response.read()

    def travel_data(self) -> Dict[str, Any]:
        """Return travel data."""
        return {
            "station": self.station,
            "stationId": self.station_id,
            "filter": self.products_filter,
            "journeys": self.build_journey_list(),
        }

    def build_journey_list(self) -> List[Dict]:
        """Build list of journeys."""
        return [
            j.as_dict()
            for j in sorted(self.journeys, key=lambda k: k.real_departure)[
                : self.max_journeys
            ]
        ]

    @property
    def station(self) -> str:
        """Extract station name."""
        return str(self.obj.SBRes.SBReq.Start.Station.HafasName.Text.pyval)

    def current_time(self) -> datetime:
        """Extract current time."""
        try:
            _date = datetime.strptime(self.obj.SBRes.SBReq.StartT.get("date"), "%Y%m%d")
            _time = datetime.strptime(self.obj.SBRes.SBReq.StartT.get("time"), "%H:%M")
        except (ValueError, AttributeError):
            raise RMVtransportDataError()

        return datetime.combine(_date.date(), _time.time())

    def print(self) -> None:
        """Pretty print travel times."""
        result = [f"{self.station} - {self.now}"]

        for j in sorted(self.journeys, key=lambda k: k.real_departure)[
            : self.max_journeys
        ]:
            result.append("-------------")
            result.append(f"{j.product}: {j.number} ({j.train_id})")
            result.append(f"Richtung: {j.direction}")
            result.append(f"Abfahrt in {j.real_departure} min.")
            result.append(f"Abfahrt {j.departure.time()} (+{j.delay})")
            result.append(f"Nächste Haltestellen: {(j.stops)}")
            if j.info:
                result.append(f"Hinweis: {j.info}")
                result.append(f"Hinweis (lang): {j.info_long}")
            result.append(f"Icon: {j.icon}")

        print("\n".join(result))


def product_filter(products) -> str:
    """Calculate the product filter."""
    _filter = sum({PRODUCTS[p] for p in products})
    return format(_filter, "b")[::-1]


def base_url(path: str = STBOARD_PATH) -> str:
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


def extract_data_from_xml(xml: bytes) -> Any:
    """Extract data from xml."""
    retry = 0
    while retry < MAX_RETRIES:
        try:
            return objectify.fromstring(xml)

        except etree.XMLSyntaxError as err:
            xml = fix_xml(xml, err)
            retry -= 1


def fix_xml(data: bytes, err: etree.XMLSyntaxError) -> Any:
    """Try to fix known issues in XML data."""
    xml_issue = data.decode().split("\n")[err.lineno - 1]

    if xml_issue not in KNOWN_XML_ISSUES.keys():
        _LOGGER.debug("Unknown xml issue in: %s", xml_issue)
        raise RMVtransportError()

    return data.decode().replace(xml_issue, KNOWN_XML_ISSUES[xml_issue]).encode()


def extract_json_data(response) -> str:
    """Extract json from response."""
    data = response.decode("utf-8")
    return str(data[data.find("{") : data.rfind("}") + 1])  # noqa: E203
