"""Define tests for the client object."""
# pylint: disable=redefined-outer-name,unused-import
import json
from datetime import datetime
from lxml import etree

import mock
import pytest

import RMVtransport


def date_hook(json_dict):
    """JSON datetime parser."""
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            pass
    return json_dict


@mock.patch('urllib.request.urlopen')
def test_getdepartures(mock_urlopen, capsys):
    """Test departures with defautl setings."""
    with open('fixtures/request.xml') as xml_file:
        xml = xml_file.read()
    with open('fixtures/result_simple.json') as json_file:
        result = json.load(json_file, object_hook=date_hook)
    with open('fixtures/result_simple.txt') as txt_file:
        output_result = txt_file.read()
    cm = mock.MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = xml
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    data = rmv.get_departures(stationId)
    assert data == result

    rmv.output()
    out, err = capsys.readouterr()
    assert out == output_result


@mock.patch('urllib.request.urlopen')
def test_departures_products(mock_urlopen):
    """Test products filter."""
    with open('fixtures/request.xml') as xml_file:
        xml = xml_file.read()
    with open('fixtures/result_products_filter.json') as json_file:
        result = json.load(json_file, object_hook=date_hook)
    cm = mock.MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = xml
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    products = ['S', 'RB']
    data = rmv.get_departures(stationId, products=products, maxJourneys=50)
    assert data == result


@pytest.mark.xfail(raises=AttributeError)
@mock.patch('urllib.request.urlopen')
def test_departures_error_xml(mock_urlopen):
    """Test with bad xml."""
    xml = "<ResC></ResC>"
    cm = mock.MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = xml
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    rmv.get_departures(stationId)


@pytest.mark.xfail(raises=etree.XMLSyntaxError)
@mock.patch('urllib.request.urlopen')
def test_no_xml(mock_urlopen):
    """Test with empty xml."""
    xml = ''
    cm = mock.MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = xml
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    rmv.get_departures(stationId)


@pytest.mark.xfail(raises=ValueError)
@mock.patch('urllib.request.urlopen')
def test_departures_error_server(mock_urlopen):
    """Test server error handling."""
    cm = mock.MagicMock()
    cm.getcode.return_value = 500
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    rmv.get_departures(stationId)


@pytest.mark.xfail(raises=TypeError)
@mock.patch('urllib.request.urlopen')
def test_departures_error_missing_argument(mock_urlopen):
    """Test missing argument handling."""
    cm = mock.MagicMock()
    cm.getcode.return_value = 500
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    rmv.get_departures()


@mock.patch('urllib.request.urlopen')
def test_departures_bad_request(mock_urlopen):
    """Test bad xml."""
    with open('fixtures/bad_request.xml') as xml_file:
        xml = xml_file.read()
    with open('fixtures/result_bad.json') as json_file:
        result = json.load(json_file, object_hook=date_hook)
    cm = mock.MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = xml
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    directionId = '3006905'
    data = rmv.get_departures(stationId, directionId)
    assert data == result


@pytest.mark.xfail(raises=AttributeError)
@mock.patch('urllib.request.urlopen')
def test_no_journeys(mock_urlopen):
    """Test with no journeys."""
    with open('fixtures/request_no_journeys.xml') as xml_file:
        xml = xml_file.read()
    cm = mock.MagicMock()
    cm.getcode.return_value = 200
    cm.read.return_value = xml
    cm.__enter__.return_value = cm
    mock_urlopen.return_value = cm

    rmv = RMVtransport.RMVtransport()
    stationId = '3006904'
    data = rmv.get_departures(stationId)
