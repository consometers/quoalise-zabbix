# Qualise proxy for Zabbix

Access data from a Zabbix instance through the Quoalise protocol.

## Client usage

Data can be accessed with the [quoalise](https://github.com/consometers/quoalise) client.

Example:

```bash
quoalise --tz Europe/Paris get-history elfe-proxy@breizh-sen2.eu/proxy urn:dev:org:60060-elfe:42878 --start-time 2023-05-01T15:00 --end-time 2023-05-01T16:00
```

## Server Usage

Install in a vitual environment:

```
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Run server with:

```
python -m qalzabbix config.json
```

`config.json`:

```json
{
    "zabbix" : {
        "url": "https://zabbix.example.com",
        "login": "…",
        "password": "…"
    },
    "xmpp" : {
        "full_jid": "zabbix-proxy@example.com/proxy",
        "password": "…"
    },
    "allowed_clients" : [
        "…",
        "…"
    ]
}
```

Resource name is currently hardcoded to be used for the [ELFE](https://www.projet-elfe.fr/) project:

```
urn:dev:org:60060-elfe:<zabbixid>
```

Note: Zabbix item id have been used as quoalise identifier because of
constraints of the ELFE project. A more stable identifier like Zabbix key
can be used to ensure it can identify a device for its life time (and after
its life time).

## Contributing

Please run black and flake8 before commit. It can be done automatically with a git pre-commit hook:

```bash
pre-commit install
```

Run integration tests with:

```
python -m qalzabbix.test_integration client.conf.json config.json
```

`client.conf.json`

```json
{
    "xmpp": {
        "bare_jid": "…",
        "password": "…"
    }
}
```