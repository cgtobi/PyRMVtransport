"""A module to query bus and train departure times."""
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import html
import json
from lxml import objectify


PRODUCTS = {
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
ALL = PRODUCTS.keys()


class RMVJourney(object):
    """A journey object to hold information about a journey."""

    def __init__(self, journey, now):
        """Initialize the journey object."""
        self.journey = journey
        self.now = now
        self.attr_types = self.journey.JourneyAttributeList.xpath(
            '*/Attribute/@type')

        self.name = self._name()
        self.number = self._number()
        self.product = self._product()
        self.trainId = self.journey.get('trainId')
        self.departure = self._departure()
        self.delay = self._delay()
        self.real_departure_time = self._real_departure_time()
        self.real_departure = self._real_departure()
        self.direction = self._direction()
        self.info = self._info()
        self.info_long = self._info_long()
        self.platform = self._platform()
        self.stops = self._pass_list()
        self.icon = self._icon()

    def _platform(self):
        """Extract platform."""
        try:
            return self.journey.MainStop.BasicStop.Dep.Platform.text
        except AttributeError:
            return None

    def _delay(self):
        """Extract departure delay."""
        try:
            return int(self.journey.MainStop.BasicStop.Dep.Delay.text)
        except AttributeError:
            return 0

    def _departure(self):
        """Extract departure time."""
        departure_time = datetime.strptime(
            self.journey.MainStop.BasicStop.Dep.Time.text,
            '%H:%M').time()
        if departure_time > (self.now - timedelta(hours=1)).time():
            return datetime.combine(self.now.date(),
                                    departure_time)
        return datetime.combine(self.now.date() + timedelta(days=1),
                                departure_time)

    def _real_departure_time(self):
        """Calculate actual departure time."""
        return self.departure + timedelta(minutes=self.delay)

    def _real_departure(self):
        """Calculate actual minutes left for departure."""
        return round((self.real_departure_time - self.now).seconds / 60)

    def _product(self):
        """Extract train product."""
        attr_product = self.journey.JourneyAttributeList.JourneyAttribute[
            self.attr_types.index('CATEGORY')].Attribute
        attr_variants = attr_product.xpath('AttributeVariant/@type')
        product = attr_product.AttributeVariant[
            attr_variants.index('NORMAL')].Text.pyval
        return product

    def _number(self):
        """Extract train number."""
        attr_number = self.journey.JourneyAttributeList.JourneyAttribute[
            self.attr_types.index('NUMBER')].Attribute
        attr_variants = attr_number.xpath('AttributeVariant/@type')
        number = attr_number.AttributeVariant[
            attr_variants.index('NORMAL')].Text.pyval
        return number

    def _name(self):
        """Extract train name."""
        attr_name = self.journey.JourneyAttributeList.JourneyAttribute[
            self.attr_types.index('NAME')].Attribute
        attr_variants = attr_name.xpath('AttributeVariant/@type')
        name = attr_name.AttributeVariant[
            attr_variants.index('NORMAL')].Text.pyval
        return name

    def _direction(self):
        """Extract train direction."""
        attr_direction = self.journey.JourneyAttributeList.JourneyAttribute[
            self.attr_types.index('DIRECTION')].Attribute
        attr_variants = attr_direction.xpath('AttributeVariant/@type')
        direction = attr_direction.AttributeVariant[
            attr_variants.index('NORMAL')].Text.pyval
        return direction

    def _info(self):
        """Extract journey information."""
        try:
            return html.unescape(
                self.journey.InfoTextList.InfoText.get('text'))
        except AttributeError:
            return None

    def _info_long(self):
        """Extract journey information."""
        try:
            return html.unescape(
                self.journey.InfoTextList.InfoText.get('textL')
                ).replace('<br />', '\n')
        except AttributeError:
            return None

    def _pass_list(self):
        """Extract next stops along the journey."""
        stops = []
        for stop in self.journey.PassList.BasicStop:
            index = stop.get('index')
            station = stop.Location.Station.HafasName.Text.text
            stationId = stop.Location.Station.ExternalId.text
            stops.append({'index': index,
                          'stationId': stationId,
                          'station': station})
        return stops

    def _icon(self):
        """Extract product icon."""
        pic_url = "https://www.rmv.de/auskunft/s/n/img/products/%i_pic.png"
        return pic_url % PRODUCTS[self.product]


class RMVtransport(object):
    """Connection data and travel information."""

    def __init__(self):
        """Initialize connection data."""
        self.base_uri = 'http://www.rmv.de/auskunft/bin/jp/'
        self.query_path = 'query.exe/'
        self.getstop_path = 'ajax-getstop.exe/'
        self.stboard_path = 'stboard.exe/'

        self.lang = 'd'
        self.type = 'n'
        self.with_suggestions = '?'

        self.http_headers = {}

        self.now = None
        self.tz = 'CET'

        self.station = None
        self.stationId = None
        self.directionId = None
        self.productsFilter = None

        self.maxJourneys = None

        self.o = None
        self.journeys = []

    def get_departures(self, stationId, directionId=None,
                       maxJourneys=20, products=ALL):
        """Fetch data from rmv.de."""
        self.stationId = stationId
        self.directionId = directionId

        self.maxJourneys = maxJourneys

        self.productsFilter = _product_filter(products)

        base_url = (self.base_uri + self.stboard_path + self.lang +
                    self.type + self.with_suggestions)
        params = {'selectDate':     'today',
                  'time':           'now',
                  'input':          self.stationId,
                  'maxJourneys':    self.maxJourneys,
                  'boardType':      'dep',
                  'productsFilter': self.productsFilter,
                  'disableEquivs':  'discard_nearby',
                  'output':         'xml',
                  'start':          'yes'}
        if self.directionId:
            params['dirInput'] = self.directionId

        url = base_url + urllib.parse.urlencode(params)
        req = urllib.request.urlopen(url)
        xml = req.read()

        try:
            self.o = objectify.fromstring(xml)
        except TypeError:
            print("Get from string", xml)
            raise

        try:
            self.now = self.current_time()
            self.station = self._station()
        except (TypeError, AttributeError):
            print("Time/Station TypeError or AttributeError",
                  objectify.dump(self.o))
            raise

        self.journeys.clear()
        try:
            for journey in self.o.SBRes.JourneyList.Journey:
                self.journeys.append(RMVJourney(journey, self.now))
        except AttributeError:
            print("Extract journeys", self.o.SBRes.Err.get('text'))
            raise

        return self.to_json()

    def to_json(self):
        """Return travel data as JSON."""
        data = {}
        data['station'] = (self.station)
        data['stationId'] = (self.stationId)
        data['filter'] = (self.productsFilter)

        journeys = []
        for j in sorted(
                self.journeys,
                key=lambda k: k.real_departure)[:self.maxJourneys]:
            journeys.append({'product': j.product,
                             'number': j.number,
                             'trainId': j.trainId,
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

    def _station(self):
        """Extract station name."""
        return self.o.SBRes.SBReq.Start.Station.HafasName.Text.pyval

    def current_time(self):
        """Extract current time."""
        if self.o is not None:
            try:
                if self.o.SBRes.SBReq is not None:
                    _date = datetime.strptime(
                        self.o.SBRes.SBReq.StartT.get("date"), '%Y%m%d')
                    _time = datetime.strptime(
                        self.o.SBRes.SBReq.StartT.get("time"), '%H:%M')
                else:
                    _date = datetime.strptime(
                        self.o.SBRes.StartT.get("date"), '%Y%m%d')
                    _time = datetime.strptime(
                        self.o.SBRes.StartT.get("time"), '%H:%M')
                return datetime.combine(_date.date(), _time.time())
            except AttributeError:
                raise

    def output(self):
        """Pretty print travel times."""
        print("%s - %s" % (self.station, self.now))
        print(self.productsFilter)

        for j in sorted(
                self.journeys,
                key=lambda k: k.real_departure)[:self.maxJourneys]:
            print("-------------")
            print("%s: %s (%s)" % (j.product, j.number, j.trainId))
            print("Richtung: %s" % (j.direction))
            print("Abfahrt in %i min." % (j.real_departure))
            print("Abfahrt %s (+%i)" % (j.departure.time(), j.delay))
            print("Nächste Haltestellen: %s" % (
                [s['station'] for s in j.stops]))
            if j.info:
                print("Hinweis: %s" % (j.info))
                print("Hinweis (lang): %s" % (j.info_long))
            print("Icon: %s" % j.icon)

    def search_station(self, station, max_results=20):
        """Search for station name."""
        base_url = (self.base_uri + self.getstop_path + self.lang +
                    self.type + self.with_suggestions)
        params = {
            'getstop': 1,
            'REQ0JourneyStopsS0A': max_results,
            'REQ0JourneyStopsS0G': station,
        }
        url = base_url + urllib.parse.urlencode(params)
        req = urllib.request.urlopen(url)
        data = req.read().decode('utf-8')
        data = json.loads(data[data.find('{'):data.rfind('}')+1])
        return [s['value'] for s in data['suggestions']]


def _product_filter(products):
    """Calculate the product filter."""
    _filter = 0
    for p in set([PRODUCTS[p] for p in products]):
        _filter += p
    return format(_filter, 'b')[::-1]
