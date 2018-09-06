# PyRMVtransport :bus:
Python library to make use of transport information from opendata.rmv.de.

[![travis](https://travis-ci.org/cgtobi/PyRMVtransport.svg?branch=master)](https://travis-ci.org/cgtobi/PyRMVtransport)
[![PyPi](https://img.shields.io/pypi/v/PyRMVtransport.svg)](https://pypi.python.org/pypi/PyRMVtransport)
[![PyPi](https://img.shields.io/pypi/pyversions/PyRMVtransport.svg)](https://pypi.python.org/pypi/PyRMVtransport)
[![PyPi](https://img.shields.io/pypi/l/PyRMVtransport.svg)](https://github.com/cgtobi/PyRMVtransport/blob/master/LICENSE)
[![codecov](https://codecov.io/gh/cgtobi/PyRMVtransport/branch/master/graph/badge.svg)](https://codecov.io/gh/cgtobi/PyRMVtransport)
[![Maintainability](https://api.codeclimate.com/v1/badges/9eeb0f9a9359b79205ad/maintainability)](https://codeclimate.com/github/cgtobi/PyRMVtransport/maintainability)

## Installation

```bash
$ pip install PyRMVtransport
```

## Usage

```python
import RMVtransport

rmv = RMVtransport.RMVtransport()

# Departures for station 3006904 (Mainz Hauptbahnhof)
rmv.get_departures(stationId='3006904')
rmv.output()

# Departures in the JSON formating for station 3006907 (Wiesbaden Hauptbahnhof)
# max. 5 results
# only specified products (S-Bahn, U-Bahn, Tram)
data = rmv.get_departures(stationId='3006907',
                          products=['S', 'U-Bahn', 'Tram'],
                          maxJourneys=5)
print(data)
```
