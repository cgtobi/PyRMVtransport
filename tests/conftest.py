import pytest


@pytest.fixture
def stops_request():
    with open("fixtures/stops.response") as f:
        return f.read()


@pytest.fixture
def xml_request():
    with open("fixtures/request.xml") as f:
        return f.read()
