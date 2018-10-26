# PyRMVtransport :bus:
Python library to make use of transport information from opendata.rmv.de.

[![travis](https://travis-ci.org/cgtobi/PyRMVtransport.svg?branch=master)](https://travis-ci.org/cgtobi/PyRMVtransport)
[![PyPi](https://img.shields.io/pypi/v/PyRMVtransport.svg)](https://pypi.python.org/pypi/PyRMVtransport)
[![PyPi](https://img.shields.io/pypi/pyversions/PyRMVtransport.svg)](https://pypi.python.org/pypi/PyRMVtransport)
[![PyPi](https://img.shields.io/pypi/l/PyRMVtransport.svg)](https://github.com/cgtobi/PyRMVtransport/blob/master/LICENSE)
[![codecov](https://codecov.io/gh/cgtobi/PyRMVtransport/branch/master/graph/badge.svg)](https://codecov.io/gh/cgtobi/PyRMVtransport)
[![Maintainability](https://api.codeclimate.com/v1/badges/9eeb0f9a9359b79205ad/maintainability)](https://codeclimate.com/github/cgtobi/PyRMVtransport/maintainability)
[![Downloads](https://pepy.tech/badge/pyrmvtransport)](https://pepy.tech/project/pyrmvtransport)

## Installation

```bash
$ pip install PyRMVtransport
```

## Usage

```python
import asyncio
import aiohttp
from RMVtransport import RMVtransport

async def main():
    """The main part of the example script."""
    async with aiohttp.ClientSession() as session:
        rmv = RMVtransport(session)

        # Get the data
        try:
            # Departures for station 3006907 (Wiesbaden Hauptbahnhof)
            # max. 5 results
            # only specified products (S-Bahn, U-Bahn, Tram)
            data = await rmv.get_departures(station_id='3006907',
                                            products=['S', 'U-Bahn', 'Tram'],
                                            max_journeys=5)

            # Use the JSON output
            print(data)

            # or pretty print
            await rmv.output()
        except TypeError:
            pass

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```
