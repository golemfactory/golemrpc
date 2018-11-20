from autobahn.asyncio.component import Component
from autobahn.asyncio.component import run
from autobahn.asyncio.wamp import ApplicationSession
from twisted.internet._sslverify import optionsForClientTLS  # noqa # pylint: disable=protected-access
from twisted.internet import reactor
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet.defer import inlineCallbacks, Deferred

import ssl

# Hardcoded golem node_A cert 
cert_path = '/home/mplebanski/Projects/golem/node_A/rinkeby/crossbar/rpc_cert.pem'

with open(cert_path, 'rb') as f:
    cert_data = f.read()

# Mismatch golem.local - localhost
ssl.match_hostname = lambda cert, hostname: True
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(cert_path)

comp = Component(
    transports=[
        {
            "type": "websocket",
            "url": "wss://localhost:61000",
            "max_retries": 1,
            "endpoint": {
                "host": "localhost",
                "type": "tcp",
                "port": 61000,
                "tls": context
            },
            "options": {
                "open_handshake_timeout": 3,
            }
        }
    ],
    authentication={
        u"wampcra": {
            u'authid': u'golemcli',
            # this key should be loaded from disk, database etc never burned into code like this...
            u'secret': '6ab5f6244f98410d9da35248ec44ac12c88950c2bb9682926946114b36b59b0c8daf521e4174c479ddc0b520fa104f4ff6356b1939feb5e21429bcf65a070c4cb22e985a13eaa8c45c36817725c6d233dae8ee51f652ecc34cc8622a184ef1cfad2f8eaf0295bdc102b152ea999927c342162efd18350d3df34863ddd6e84712',
        }
    },
    realm=u"golem",
)

from autobahn.asyncio.websocket import WampWebSocketClientProtocol
from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

@comp.on_join
async def joined(session: Session, details: SessionDetails):
    await session.subscribe(lambda response: print('status ' + str(response)),
                            u'evt.golem.status')
    await session.subscribe(lambda response: print('net_connection ' + str(response)),
                            u'evt.net.connection')
    await session.subscribe(lambda response: print('task status ' + str(response)),
                            u'evt.comp.task.status')
    await session.subscribe(lambda response: print('subtask status ' + str(response)),
                            u'evt.comp.subtask.status')
    await session.subscribe(lambda response: print('task.prov_rejected ' + str(response)),
                            u'evt.comp.task.prov_rejected')

@comp.on_connect
async def connected(session: Session, client_protocol: WampWebSocketClientProtocol):
    pass

@comp.on_disconnect
async def disconnected(session: Session, details=None, was_clean=True):
    pass

@comp.on_ready
async def ready(session: Session, details=None):
    pass

@comp.on_leave
async def leave(session, details):
    pass

if __name__ == "__main__":
    run([comp])
