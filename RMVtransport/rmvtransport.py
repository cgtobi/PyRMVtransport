"""A module to query bus and train departure times."""
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import html
import logging
from typing import List, Dict, Any, Optional, Union
import aiohttp
import async_timeout
from lxml import objectify
from lxml import etree


PRODUCTS: Dict[str, int] = {
    'ICE': 1,
    'IC': 2,
    'EC': 2,
    'RB': 4,
    'RE': 4,
    'S': 8,
    'U-Bahn': 16,
    'Tram': 32,
    'Bus': 64,
    'Bus2': 128,
    'Fähre': 256,
    'Taxi': 512,
    'Bahn': 1024,
}
ALL_PRODUCTS: List[str] = list(PRODUCTS.keys())

_LOGGER = logging.getLogger(__name__)


class RMVtransportError(Exception):
    """General RMV transport error exception occurred."""

    pass


class RMVtransportApiConnectionError(RMVtransportError):
    """When a connection error is encountered."""

    pass


class RMVJourney():
    """A journey object to hold information about a journey."""

    # pylint: disable=I1101
    def __init__(self,
                 journey: objectify.ObjectifiedElement,
                 now: datetime) -> None:
        """Initialize the journey object."""
        self.journey: objectify.ObjectifiedElement = journey
        self.now: datetime = now
        self.attr_types = self.journey.JourneyAttributeList.xpath(
            '*/Attribute/@type')

        self.name: str = self._extract('NAME')
        self.number: str = self._extract('NUMBER')
        self.product: str = self._extract('CATEGORY')
        self.train_id: str = self.journey.get('trainId')
        self.departure: datetime = self._departure()
        self.delay: int = self._delay()
        self.real_departure_time: datetime = self._real_departure_time()
        self.real_departure: int = self._real_departure()
        self.direction = self._extract('DIRECTION')
        self.info = self._info()
        self.info_long = self._info_long()
        self.platform = self._platform()
        self.stops = self._pass_list()
        self.icon = self._icon()

    def _platform(self) -> Optional[str]:
        """Extract platform."""
        try:
            return self.journey.MainStop.BasicStop.Dep.Platform.text
        except AttributeError:
            return None

    def _delay(self) -> int:
        """Extract departure delay."""
        try:
            return int(self.journey.MainStop.BasicStop.Dep.Delay.text)
        except AttributeError:
            return 0

    def _departure(self) -> datetime:
        """Extract departure time."""
        departure_time = datetime.strptime(
            self.journey.MainStop.BasicStop.Dep.Time.text,
            '%H:%M').time()
        if departure_time > (self.now - timedelta(hours=1)).time():
            return datetime.combine(self.now.date(),
                                    departure_time)
        return datetime.combine(self.now.date() + timedelta(days=1),
                                departure_time)

    def _real_departure_time(self) -> datetime:
        """Calculate actual departure time."""
        return self.departure + timedelta(minutes=self.delay)

    def _real_departure(self) -> int:
        """Calculate actual minutes left for departure."""
        return round((self.real_departure_time - self.now).seconds / 60)

    def _extract(self, attribute):
        """Extract train information."""
        attr_data = self.journey.JourneyAttributeList.JourneyAttribute[
            self.attr_types.index(attribute)].Attribute
        attr_variants = attr_data.xpath('AttributeVariant/@type')
        data = attr_data.AttributeVariant[
            attr_variants.index('NORMAL')].Text.pyval
        return data

    def _info(self) -> Optional[str]:
        """Extract journey information."""
        try:
            return html.unescape(
                self.journey.InfoTextList.InfoText.get('text'))
        except AttributeError:
            return None

    def _info_long(self) -> Optional[str]:
        """Extract journey information."""
        try:
            return html.unescape(
                self.journey.InfoTextList.InfoText.get('textL')
                ).replace('<br />', '\n')
        except AttributeError:
            return None

    def _pass_list(self) -> List[Dict[str, Any]]:
        """Extract next stops along the journey."""
        stops: List[Dict[str, Any]] = []
        for stop in self.journey.PassList.BasicStop:
            index = stop.get('index')
            station = stop.Location.Station.HafasName.Text.text
            station_id = stop.Location.Station.ExternalId.text
            stops.append({'index': index,
                          'stationId': station_id,
                          'station': station})
        return stops

    def _icon(self) -> str:
        """Extract product icon."""
        pic_url = "https://www.rmv.de/auskunft/s/n/img/products/%i_pic.png"
        return pic_url % PRODUCTS[self.product]


class RMVtransport():
    """Connection data and travel information."""

    def __init__(self,
                 session: aiohttp.ClientSession,
                 timeout: int = 10) -> None:
        """Initialize connection data."""
        self._session: aiohttp.ClientSession = session
        self._timeout: int = timeout

        self.base_uri: str = 'http://www.rmv.de/auskunft/bin/jp/'
        self.query_path: str = 'query.exe/'
        self.getstop_path: str = 'ajax-getstop.exe/'
        self.stboard_path: str = 'stboard.exe/'

        self.lang: str = 'd'
        self.type: str = 'n'
        self.with_suggestions: str = '?'

        # self.http_headers: Dict = {}

        self.now: datetime
        # self.timezone: str = 'CET'

        self.station: str
        self.station_id: str
        self.direction_id: Optional[str] = None
        self.products_filter: str

        self.max_journeys: int

        self.obj: objectify.ObjectifiedElement  # pylint: disable=I1101
        self.journeys: List[RMVJourney] = []

    async def get_departures(self,
                             station_id: str,
                             direction_id: str = None,
                             max_journeys: int = 20,
                             products: List[str] = None) -> Dict[str, Any]:
        """Fetch data from rmv.de."""
        self.station_id: str = station_id
        self.direction_id: str = direction_id

        self.max_journeys: int = max_journeys

        self.products_filter: str = _product_filter(products or ALL_PRODUCTS)

        base_url: str = self._base_url()
        params: Dict[str, Union[str, int]] = {
            'selectDate':     'today',
            'time':           'now',
            'input':          self.station_id,
            'maxJourneys':    self.max_journeys,
            'boardType':      'dep',
            'productsFilter': self.products_filter,
            'disableEquivs':  'discard_nearby',
            'output':         'xml',
            'start':          'yes'}
        if self.direction_id:
            params['dirInput'] = self.direction_id

        url = base_url + urllib.parse.urlencode(params)

        try:
            with async_timeout.timeout(self._timeout):
                async with self._session.get(url) as response:
                    _LOGGER.debug(
                        "Response from RMV API: %s", response.status)
                    xml = await response.read()
                    _LOGGER.debug(xml)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load data from RMV API")
            raise RMVtransportApiConnectionError()

        # pylint: disable=I1101
        try:
            self.obj = objectify.fromstring(xml)
        except (TypeError, etree.XMLSyntaxError):
            _LOGGER.debug("Get from string: %s", xml[:100])
            print("Get from string: %s" % xml)
            raise RMVtransportError()

        try:
            self.now = self.current_time()
            self.station = self._station()
        except (TypeError, AttributeError):
            _LOGGER.debug("Time/Station TypeError or AttributeError %s",
                          objectify.dump(self.obj))
            raise RMVtransportError()

        self.journeys.clear()
        try:
            for journey in self.obj.SBRes.JourneyList.Journey:
                self.journeys.append(RMVJourney(journey, self.now))
        except AttributeError:
            _LOGGER.debug("Extract journeys: %s",
                          self.obj.SBRes.Err.get('text'))
            raise RMVtransportError()

        return self.data()

    def data(self) -> Dict[str, Any]:
        """Return travel data."""
        data: Dict[str, Any] = {}
        data['station'] = (self.station)
        data['stationId'] = (self.station_id)
        data['filter'] = (self.products_filter)

        journeys = []
        for j in sorted(
                self.journeys,
                key=lambda k: k.real_departure)[:self.max_journeys]:
            journeys.append({'product': j.product,
                             'number': j.number,
                             'trainId': j.train_id,
                             'direction': j.direction,
                             'departure_time': j.real_departure_time,
                             'minutes': j.real_departure,
                             'delay': j.delay,
                             'stops': [s['station'] for s in j.stops],
                             'info': j.info,
                             'info_long': j.info_long,
                             'icon': j.icon})
        data['journeys'] = (journeys)
        return data

    def _base_url(self) -> str:
        """Build base url."""
        return (self.base_uri + self.stboard_path + self.lang +
                self.type + self.with_suggestions)

    def _station(self) -> str:
        """Extract station name."""
        return self.obj.SBRes.SBReq.Start.Station.HafasName.Text.pyval

    def current_time(self) -> datetime:
        """Extract current time."""
        try:
            _date = datetime.strptime(
                self.obj.SBRes.SBReq.StartT.get("date"), '%Y%m%d')
            _time = datetime.strptime(
                self.obj.SBRes.SBReq.StartT.get("time"), '%H:%M')
            return datetime.combine(_date.date(), _time.time())
        except AttributeError:
            raise RMVtransportError

    def output(self) -> None:
        """Pretty print travel times."""
        print("%s - %s" % (self.station, self.now))
        print(self.products_filter)

        for j in sorted(
                self.journeys,
                key=lambda k: k.real_departure)[:self.max_journeys]:
            print("-------------")
            print("%s: %s (%s)" % (j.product, j.number, j.train_id))
            print("Richtung: %s" % (j.direction))
            print("Abfahrt in %i min." % (j.real_departure))
            print("Abfahrt %s (+%i)" % (j.departure.time(), j.delay))
            print("Nächste Haltestellen: %s" % (
                [s['station'] for s in j.stops]))
            if j.info:
                print("Hinweis: %s" % (j.info))
                print("Hinweis (lang): %s" % (j.info_long))
            print("Icon: %s" % j.icon)


def _product_filter(products) -> str:
    """Calculate the product filter."""
    _filter = 0
    for product in {PRODUCTS[p] for p in products}:
        _filter += product
    return format(_filter, 'b')[::-1]
