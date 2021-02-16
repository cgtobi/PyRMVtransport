"""This class represents a single journey."""
import html
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from lxml import objectify  # type: ignore

from .const import IMG_URL, PRODUCTS

_LOGGER = logging.getLogger(__name__)


class RMVJourney:
    """A journey object to hold information about a journey."""

    # pylint: disable=I1101
    def __init__(self, journey: objectify.ObjectifiedElement, now: datetime) -> None:
        """Initialize the journey object."""
        self._journey: objectify.ObjectifiedElement = journey
        self._now: datetime = now
        self._attr_types = self._journey.JourneyAttributeList.xpath("*/Attribute/@type")

    def as_dict(self) -> Dict:
        """Build journey dictionary."""
        return {
            "product": self.product,
            "number": self.number,
            "trainId": self.train_id,
            "direction": self.direction,
            "departure_time": self.real_departure_time,
            "minutes": self.real_departure,
            "delay": self.delay,
            "stops": self.stops,
            "info": self.info,
            "info_long": self.info_long,
            "icon": self.icon,
        }

    @property
    def number(self) -> str:
        """Return the number of the route."""
        return self._extract("NUMBER")

    @property
    def product(self) -> str:
        """Return the product category."""
        return self._extract("CATEGORY")

    @property
    def train_id(self) -> str:
        """Return the train id."""
        return str(self._journey.get("trainId"))

    @property
    def departure(self) -> datetime:
        """Return time of departure."""
        return self._departure()

    @property
    def delay(self) -> int:
        """Return current delay for departure."""
        return self._delay()

    @property
    def real_departure_time(self) -> datetime:
        """Return the real departure time."""
        return self._real_departure_time()

    @property
    def real_departure(self) -> int:
        """Return minutes until departure."""
        return self._real_departure()

    @property
    def direction(self) -> str:
        """Return the direction of travel."""
        return self._extract("DIRECTION")

    @property
    def info(self) -> Optional[str]:
        """Return journey information."""
        return self._info()

    @property
    def info_long(self) -> Optional[str]:
        """Return long journey information."""
        return self._info_long()

    @property
    def _stops(self) -> List[Dict]:
        """Return list of stops along the journey."""
        return self._pass_list()

    @property
    def stops(self) -> List[str]:
        """Return list of stops along the journey."""
        return [s["station"] for s in self._stops]

    @property
    def icon(self) -> str:
        """Return icon url for the means of transport."""
        return self._icon()

    def _delay(self) -> int:
        """Extract departure delay."""
        try:
            return int(self._journey.MainStop.BasicStop.Dep.Delay.text)
        except AttributeError:
            return 0

    def _departure(self) -> datetime:
        """Extract departure time."""
        departure_time = datetime.strptime(
            self._journey.MainStop.BasicStop.Dep.Time.text, "%H:%M"
        ).time()
        if departure_time > (self._now - timedelta(hours=1)).time():
            return datetime.combine(self._now.date(), departure_time)
        return datetime.combine(self._now.date() + timedelta(days=1), departure_time)

    def _real_departure_time(self) -> datetime:
        """Calculate actual departure time."""
        return self.departure + timedelta(minutes=self.delay)

    def _real_departure(self) -> int:
        """Calculate actual minutes left for departure."""
        return round((self.real_departure_time - self._now).seconds / 60)

    def _extract(self, attribute) -> str:
        """Extract train information."""
        attr_data = self._journey.JourneyAttributeList.JourneyAttribute[
            self._attr_types.index(attribute)
        ].Attribute
        attr_variants = attr_data.xpath("AttributeVariant/@type")
        try:
            data = attr_data.AttributeVariant[attr_variants.index("NORMAL")].Text.pyval
        except ValueError:
            return ""
        return str(data)

    def _info(self) -> Optional[str]:
        """Extract journey information."""
        try:
            return str(html.unescape(self._journey.InfoTextList.InfoText.get("text")))
        except AttributeError:
            return None

    def _info_long(self) -> Optional[str]:
        """Extract journey information."""
        try:
            return str(
                html.unescape(self._journey.InfoTextList.InfoText.get("textL")).replace(
                    "<br />", "\n"
                )
            )
        except AttributeError:
            return None

    def _pass_list(self) -> List[Dict[str, Any]]:
        """Extract next stops along the journey."""
        stops: List[Dict[str, Any]] = []
        for stop in self._journey.PassList.BasicStop:
            index = stop.get("index")
            station = stop.Location.Station.HafasName.Text.text
            station_id = stop.Location.Station.ExternalId.text
            stops.append({"index": index, "stationId": station_id, "station": station})
        return stops

    def _icon(self) -> str:
        """Extract product icon."""
        pic_url = IMG_URL
        try:
            return pic_url % PRODUCTS[self.product]
        except KeyError:
            _LOGGER.debug("No matching icon for product: %s", self.product)
            return pic_url % PRODUCTS["Bahn"]
