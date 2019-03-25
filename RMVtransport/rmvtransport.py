"""A module to query bus and train departure times."""
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional, Union
import aiohttp
import async_timeout
from lxml import objectify, etree  # type: ignore

from .errors import RMVtransportError, RMVtransportApiConnectionError
from .rmvjourney import RMVJourney
from .const import PRODUCTS, ALL_PRODUCTS

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
        self.station_id: str = station_id
        self.direction_id: str = direction_id

        self.max_journeys: int = max_journeys

        self.products_filter: str = _product_filter(products or ALL_PRODUCTS)

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

        try:
            with async_timeout.timeout(self._timeout):
                async with self._session.get(url) as response:
                    _LOGGER.debug(f"Response from RMV API: {response.status}")
                    xml = await response.read()
                    _LOGGER.debug(xml)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load data from RMV API")
            raise RMVtransportApiConnectionError()

        # pylint: disable=I1101
        try:
            self.obj = objectify.fromstring(xml)
        except (TypeError, etree.XMLSyntaxError):
            _LOGGER.debug(f"Get from string: {xml[:100]}")
            print(f"Get from string: {xml}")
            raise RMVtransportError()

        try:
            self.now = self.current_time()
            self.station = self._station()
        except (TypeError, AttributeError):
            _LOGGER.debug(
                f"Time/Station TypeError or AttributeError {objectify.dump(self.obj)}"
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


def _base_url() -> str:
    """Build base url."""
    _lang: str = "d"
    _type: str = "n"
    _with_suggestions: str = "?"
    return BASE_URI + STBOARD_PATH + _lang + _type + _with_suggestions
