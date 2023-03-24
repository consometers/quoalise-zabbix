#!/usr/bin/env python3

import asyncio
import logging
import json
from typing import List, Mapping, Tuple
from dataclasses import dataclass
from pyzabbix import ZabbixAPI
import re
from abc import ABC, abstractmethod
import datetime as dt

from slixmpp.xmlstream import ElementBase

from quoalise.server import ServerAsync, GetHistoryHandler
from quoalise.data import Record, Data


@dataclass
class ZabbixItemInfo:
    id: int
    key: str
    unit: str


class ZabbixItemResolver(ABC):
    """
    User provided resolver to find zabbix API and item ids from URN identifiers.

    The URN should be a globally unique name, persistent even when the resource
    cease to exist, directly using a Zabbix identifer in the URN does not seem
    to be a goode idea. If the device name/id cannot be infered at the proxy
    side, but can but on the client side, URN r-components might be useful
    """

    @abstractmethod
    def resolve(self, urn_identifier: str) -> Tuple[ZabbixAPI, ZabbixItemInfo]:
        pass


class ZabbixItemResolverConsometers(ZabbixItemResolver):
    """
    Consometers project specific identifiers.

    For now we just assume the zabbix key will be found at the end of the
    resource.
    """

    IDENTIFIER_REGEX = re.compile(r"^urn:dev:org:32473-.*:(\w+)$")

    def __init__(self, zabbix_api: ZabbixAPI):
        self.zabbix_api = zabbix_api
        self.item_from_key: Mapping[str, ZabbixItemInfo] = {}

    def resolve(self, urn_identifier: str) -> Tuple[ZabbixAPI, ZabbixItemInfo]:

        m = re.match(self.IDENTIFIER_REGEX, urn_identifier)
        if not m:
            raise ValueError(f"{urn_identifier} identifier is not supported")

        item_key = m.group(1)
        # FIXME handle renamings, resolve periodically?
        if item_key not in self.item_from_key:
            self.update_mapping()

        item_info = self.item_from_key.get(item_key)

        if item_info is None:
            raise ValueError(f"Item with key {item_key} not found")

        return self.zabbix_api, item_info

    def update_mapping(self):
        self.item_from_key.clear()
        items = self.zabbix_api.item.get()
        for item in items:
            key = item["key_"]
            if "_" in key and "[" not in key:
                item_info = ZabbixItemInfo(
                    id=item["itemid"], key=key, unit=item["units"]
                )
                self.item_from_key[key] = item_info


def datetime_to_zabbix(date):
    assert date.tzinfo is not None, "Naive datetimes are not handled to prevent errors"
    utc_date = date.astimezone(dt.timezone.utc)
    return utc_date.timestamp()


def zabbix_to_datetime(clock: int, ns: float) -> dt.datetime:
    timestamp = clock + ns / 1e9
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)


class GetZabbixHistoryHandler(GetHistoryHandler):

    MAX_RECORDS = 5000

    def __init__(self, zabbix_resolver: ZabbixItemResolver):
        super().__init__()
        self.zabbix_resolver = zabbix_resolver

    def default_identifier(self) -> str:
        return "urn:dev:org:32473-elfe:C013_batterie"

    def get_history(self, client, identifier, start_time, end_time):

        zabbix_api, requested_item = self.zabbix_resolver.resolve(identifier)

        records = []

        while start_time < end_time:

            end_time_limited = min(end_time, start_time + dt.timedelta(days=1))

            history = zabbix_api.history.get(
                itemids=[requested_item.id],
                time_from=int(datetime_to_zabbix(start_time)),
                time_till=int(datetime_to_zabbix(end_time_limited)),
                output="extend",
                limit=self.MAX_RECORDS + 1,
                history=0,
            )

            start_time = end_time_limited

            for item in history:
                assert item["itemid"] == requested_item.id
                record = Record(
                    name=identifier,
                    time=zabbix_to_datetime(int(item["clock"]), float(item["ns"])),
                    value=float(item["value"]),
                    unit=requested_item.unit,
                )
                records.append(record)

        class Quoalise(ElementBase):
            name = "quoalise"
            namespace = "urn:quoalise:0"

        quoalise_element = Quoalise()

        if len(records) > self.MAX_RECORDS:
            raise ValueError(
                f"Response would be too big (max {self.MAX_RECORDS} records)."
            )

        data = Data(metadata=None, records=records)
        quoalise_element.append(data.to_xml())

        return quoalise_element


async def main(conf):

    zabbix_api = ZabbixAPI(conf["zabbix"]["url"])
    zabbix_api.login(conf["zabbix"]["login"], conf["zabbix"]["password"])

    zabbix_resolver = ZabbixItemResolverConsometers(zabbix_api)

    server = await ServerAsync.connect(
        conf["xmpp"]["full_jid"], conf["xmpp"]["password"]
    )
    get_zabbix_history = GetZabbixHistoryHandler(zabbix_resolver)
    server.add_handler(get_zabbix_history)


if __name__ == "__main__":

    import argparse

    logging.basicConfig()
    debug: List[str] = []

    debug.append("slixmpp")

    for logger_name in debug:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = True

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "conf", help="Configuration file (typically private/*.conf.json)"
    )
    args = parser.parse_args()

    with open(args.conf, "r") as f:
        conf = json.load(f)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main(conf))
    loop.run_forever()
