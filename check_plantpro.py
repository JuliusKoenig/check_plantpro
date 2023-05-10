import argparse
import logging
import sys
import time

import bs4
import requests
from bs4 import BeautifulSoup

TITLE = "check_plantpro"
VERSION = "0.1.2"
AUTHOR = "Julius König"

# configure logging
logging.basicConfig()

logger = logging.getLogger(__name__)


def _version():
    print(f"{TITLE} {VERSION} by {AUTHOR}")


def nagios_exit(ec: int, em: str = None, pd: str = None):
    logger.debug(f"exit_code: {ec}, exit_message: {em}, perf_data: {pd}")
    m = ""
    if em:
        m = em
    if pd:
        m += f" | {pd}"
    if m:
        print(m)
    sys.exit(ec)


def _post(url: str, form_data: dict) -> requests.Response:
    try:
        logger.debug(f"POST {url} with data: {form_data}")
        response = requests.post(url, data=form_data, timeout=args.timeout)
        logger.debug(f"response: {response}")

        if response.status_code != 200:
            raise Exception("POST failed")
        return response
    except Exception as e:
        logger.exception(e)
        nagios_exit(3, f"POST {url} failed")


def _form(id_menu: str, go: str, id_button: str) -> dict:
    time_since_epoch: int = int(time.time())

    form_data: dict = {
        "timestamp": time_since_epoch,
        "msg": "",
        "idmenu": id_menu,
        "go": go,
        "idbutton": id_button,
    }

    return form_data


def _login():
    url: str = f"http://{args.host}:{args.port}/001.t"

    logger.debug(f"login with user: {args.user}")

    form_data = _form("", "003.t", "13")
    form_data.update({
        4: args.user,
        5: args.password,
    })

    response = _post(url, form_data)
    html = response.content.decode(args.encoding)
    authenticated = "form action=\"003.t\"" in html
    # if not authenticated:
    #     nagios_exit(3, "Login failed")


def _get_alarms() -> list:
    url: str = f"http://{args.host}:{args.port}/037.t"

    out = []

    form_data = _form("3", "037.t", "9")
    form_data.update({
        "idline": "0"
    })

    response = _post(url, form_data)
    form_data.update({"idbutton": "4"})
    html = response.content.decode(args.encoding)
    soup = BeautifulSoup(html, 'html.parser')

    data_soup = soup.find(id="datat").next
    if isinstance(data_soup, bs4.element.NavigableString):
        data_str = str(data_soup)
        data = data_str.split("^")

        for d in data:
            alarm = d.replace("|", " - ")
            out.append(alarm)
    return out


def _get_sensors() -> dict:
    url: str = f"http://{args.host}:{args.port}/003.t"

    sensors = {}

    form_data = _form("", "003.t", "13")
    form_data.update({
        "idline": "0"
    })

    while True:
        response = _post(url, form_data)
        data_added = False
        form_data.update({"idbutton": "4"})
        html = response.content.decode(args.encoding)
        soup = BeautifulSoup(html, 'html.parser')

        # get element with id="datat"
        data = soup.find(id="datat").next
        data_str = str(data)
        current_module_name = ""
        for v in data_str.split("^"):
            a = v.split("|")
            if a[1] != "":
                current_module_name = a[1]
            name = f"{current_module_name}.{a[2]}"
            value = float(a[3].split(" ")[0])
            unit = a[3].split(" ")[1]
            if name not in sensors:
                sensors[name] = {"value": value, "unit": unit}
                data_added = True

        if not data_added:
            break

    return sensors


if __name__ == '__main__':
    retry = 0
    args = argparse.ArgumentParser()
    args.add_argument("-H", "--host", help="Hostname or Ipaddress", required=True)
    args.add_argument("-P", "--port", help="Port", default=80)
    args.add_argument("-t", "--timeout", help="HTTP Timeout", default=5, type=int)
    args.add_argument("-e", "--encoding", help="Encoding for Web-scrapping", default="utf-8")
    args.add_argument("-u", "--user", help="Auth user", default="monitoring")
    args.add_argument("-p", "--password", help="Auth password", default="")
    args.add_argument("-v", "--verbose", help="Verbose", action="store_true")
    args.add_argument("-V", "--version", help="Version", action="store_true")
    args.add_argument("-w", "--warning", help="Warning Threshold", default=None, type=float)
    args.add_argument("-c", "--critical", help="critical Threshold", default=None, type=float)
    args.add_argument("-f", "--filter", help="Filter by sensor name. For example: 'I/O-Modul 1.Kuehlung'", default="")
    args.add_argument("-r", "--retry", help="Retry", default=10, type=int)

    args = args.parse_args()

    if args.version:
        _version()
        nagios_exit(0)

    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    logger.debug(f"args: {args}")
    sensors, alarms = None, None
    while retry < args.retry:
        logger.debug(f"retry: {retry}/{args.retry}")
        try:
            retry += 1
            _login()
            sensors = _get_sensors()
            alarms = _get_alarms()
            break
        except Exception as e:
            logger.debug(e)
            time.sleep(3)
            continue
    if sensors is None or alarms is None:
        logger.error("Could not get data")
        nagios_exit(3, "Could not get data")

    exit_code = 0
    exit_message = ""
    if len(alarms) > 0:
        exit_code = 2
        exit_message = f"Got '{len(alarms)}' alarms\\n"
        for a in alarms:
            exit_message += f"{a}\\n"

    filtered_sensors = {}
    for k, v in sensors.items():
        if args.filter in k:
            filtered_sensors[k] = v

    for k, v in filtered_sensors.items():
        if args.warning is not None:
            if v["value"] > args.warning:
                exit_code = 1
        if args.critical is not None:
            if v["value"] > args.critical:
                exit_code = 2
        if exit_code == 1:
            exit_message += f"Warning: {k} is {v['value']} {v['unit']}\\n"
        elif exit_code == 2:
            exit_message += f"Critical: {k} is {v['value']} {v['unit']}\\n"
    if exit_code == 0:
        if args.filter != "":
            if len(filtered_sensors) == 0:
                nagios_exit(3, f"Sensor '{args.filter}' not found")
            value = list(filtered_sensors.values())[0]["value"]
            unit = list(filtered_sensors.values())[0]["unit"]
            exit_message = f"{value} {unit}"
        else:
            exit_message = "All Sensors OK"
    else:
        exit_message = exit_message[:-2]

    perf_data = ""
    for k, v in filtered_sensors.items():
        w = args.warning if args.warning is not None else ""
        c = args.critical if args.critical is not None else ""
        perf_data += f"'{k}'={v['value']}{v['unit']};{w};{c};; "

    nagios_exit(exit_code, exit_message, perf_data)
