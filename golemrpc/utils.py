import os 
import ssl

from autobahn.asyncio.component import Component
from pathlib import Path

from .core_imports import TaskOp

def create_component(datadir=None, host='localhost', port=61000):

    if os.name == 'nt':
        raise NotImplementedError('Fix default datatdir for Windows')

    if not datadir:
        datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

    secret_path = '{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir)

    # Mismatch golem.local - localhost
    ssl.match_hostname = lambda cert, hostname: True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(
        '{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
    )

    with open(secret_path, 'rb') as secretf:
        wampcra_secret = secretf.read()

    component = Component(
        transports=[
            {
                "type": "websocket",
                "url": "wss://{host}:{port}".format(host=host, port=port),
                "max_retries": 1,
                "endpoint": {
                    "host": host,
                    "type": "tcp",
                    "port": port,
                    "tls": context
                },
                "options": {
                    "open_handshake_timeout": 3,
                }
            }
        ],
        authentication={
            u"wampcra": {
                u'authid': 'golemcli',
                u'secret': wampcra_secret
            }
        },
        realm=u"golem",
    )
    return component
