"""Python library to make use of transport information from opendata.rmv.de."""
# pylint: disable=C0103
from .rmvtransport import RMVtransport  # noqa

MAJOR_VERSION = 0
MINOR_VERSION = 3
PATCH_VERSION = 1
__version__ = f"{MAJOR_VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
