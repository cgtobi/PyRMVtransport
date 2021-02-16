from datetime import datetime

URL = "www.rmv.de"
URL_PATH = "/auskunft/bin/jp/stboard.exe/dn"
URL_SEARCH_PATH = "/auskunft/bin/jp/ajax-getstop.exe/dn"


def date_hook(json_dict):
    """JSON datetime parser."""
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            pass
    return json_dict
