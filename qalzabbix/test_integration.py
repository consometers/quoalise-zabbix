#!/usr/bin/env python3

import asyncio

import unittest
import quoalise
import datetime as dt

CONF_CLIENT = None
CONF_PROXY = None


class TestGetMeasurement(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()

        self.client = quoalise.Client.connect(
            CONF_CLIENT["xmpp"]["bare_jid"],
            CONF_CLIENT["xmpp"]["password"],
        )

        self.proxy = CONF_PROXY["xmpp"]["full_jid"]

    def tearDown(self):
        self.client.disconnect()

    def test_get_authorized_consumption_power_active(self):
        measurement = "urn:dev:org:60060-elfe:A019_puissance"
        end_time = dt.datetime.now(dt.timezone.utc).astimezone() - dt.timedelta(days=1)
        start_time = end_time - dt.timedelta(minutes=60)
        data = self.client.get_history(self.proxy, measurement, start_time, end_time)
        records = list(data.records)
        print(records)
        self.assertGreaterEqual(len(records), 0)
        self.assertEqual(records[0].name, measurement)


if __name__ == "__main__":

    import sys
    import argparse
    import logging
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("conf_client", help="Client configuration file")
    parser.add_argument("conf_proxy", help="Proxy configuration file")
    args, unittest_args = parser.parse_known_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    with open(args.conf_client, "r") as f:
        CONF_CLIENT = json.load(f)

    with open(args.conf_proxy, "r") as f:
        CONF_PROXY = json.load(f)

    unittest.main(argv=[sys.argv[0]] + unittest_args)
