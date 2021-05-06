"""This class represents a collection of journeys."""
from collections import UserDict
from typing import Dict, List

from .const import SEPARATOR
from .rmvjourney import RMVjourney


class RMVtravel(UserDict):
    """A travle object to hold information about a collection of journeys."""

    def __init__(
        self,
        station: str,
        station_id: str,
        products_filter: str,
        journeys: List[RMVjourney],
        max_journeys: int,
    ):
        self.journeys = journeys
        self.iter = iter(build_journey_list(journeys, max_journeys))
        super().__init__(
            {
                "station": station,
                "stationId": station_id,
                "filter": products_filter,
                "journeys": list(self.iter),
            }
        )

    def __str__(self) -> str:
        """Pretty print travel times."""
        result = [str(j) for j in self.journeys]
        return f"{SEPARATOR}".join(result)


def build_journey_list(journeys, max_journeys) -> List[Dict]:
    """Build list of journeys."""
    k = lambda k: k.real_departure  # noqa: E731
    return [j.as_dict() for j in sorted(journeys, key=k)[:max_journeys]]
