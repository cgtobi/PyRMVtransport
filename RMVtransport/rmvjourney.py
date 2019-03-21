"""This class represents a single journey."""
from datetime import datetime, timedelta
import html
from typing import List, Dict, Any, Optional
from lxml import objectify  # type: ignore

from .const import PRODUCTS


class RMVJourney:
    """A journey object to hold information about a journey."""

    # pylint: disable=I1101
    def __init__(self, journey: objectify.ObjectifiedElement, now: datetime) -> None:
        """Initialize the journey object."""
        self.journey: objectify.ObjectifiedElement = journey
        self.now: datetime = now
        self.attr_types = self.journey.JourneyAttributeList.xpath("*/Attribute/@type")

        self.name: str = self._extract("NAME")
        self.number: str = self._extract("NUMBER")
        self.product: str = self._extract("CATEGORY")
        self.train_id: str = self.journey.get("trainId")
        self.departure: datetime = self._departure()
        self.delay: int = self._delay()
        self.real_departure_time: datetime = self._real_departure_time()
        self.real_departure: int = self._real_departure()
        self.direction = self._extract("DIRECTION")
        self.info = self._info()
        self.info_long = self._info_long()
        self.platform = self._platform()
        self.stops = self._pass_list()
        self.icon = self._icon()

    def _platform(self) -> Optional[str]:
        """Extract platform."""
        try:
            return str(self.journey.MainStop.BasicStop.Dep.Platform.text)
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
            self.journey.MainStop.BasicStop.Dep.Time.text, "%H:%M"
        ).time()
        if departure_time > (self.now - timedelta(hours=1)).time():
            return datetime.combine(self.now.date(), departure_time)
        return datetime.combine(self.now.date() + timedelta(days=1), departure_time)

    def _real_departure_time(self) -> datetime:
        """Calculate actual departure time."""
        return self.departure + timedelta(minutes=self.delay)

    def _real_departure(self) -> int:
        """Calculate actual minutes left for departure."""
        return round((self.real_departure_time - self.now).seconds / 60)

    def _extract(self, attribute) -> str:
        """Extract train information."""
        attr_data = self.journey.JourneyAttributeList.JourneyAttribute[
            self.attr_types.index(attribute)
        ].Attribute
        attr_variants = attr_data.xpath("AttributeVariant/@type")
        data = attr_data.AttributeVariant[attr_variants.index("NORMAL")].Text.pyval
        return str(data)

    def _info(self) -> Optional[str]:
        """Extract journey information."""
        try:
            return str(html.unescape(self.journey.InfoTextList.InfoText.get("text")))
        except AttributeError:
            return None

    def _info_long(self) -> Optional[str]:
        """Extract journey information."""
        try:
            return str(
                html.unescape(self.journey.InfoTextList.InfoText.get("textL")).replace(
                    "<br />", "\n"
                )
            )
        except AttributeError:
            return None

    def _pass_list(self) -> List[Dict[str, Any]]:
        """Extract next stops along the journey."""
        stops: List[Dict[str, Any]] = []
        for stop in self.journey.PassList.BasicStop:
            index = stop.get("index")
            station = stop.Location.Station.HafasName.Text.text
            station_id = stop.Location.Station.ExternalId.text
            stops.append({"index": index, "stationId": station_id, "station": station})
        return stops

    def _icon(self) -> str:
        """Extract product icon."""
        pic_url = "https://www.rmv.de/auskunft/s/n/img/products/%i_pic.png"
        return pic_url % PRODUCTS[self.product]
