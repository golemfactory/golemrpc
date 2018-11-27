from autobahn.asyncio.component import Component
from autobahn.asyncio.websocket import WampWebSocketClientProtocol
from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

import asyncio
import cloudpickle
import logging
import ssl
import txaio

log = txaio.make_logger()

def component_get():
    cert_path = '/home/mplebanski/Projects/golem/node_A/rinkeby/crossbar/rpc_cert.pem'

    with open(cert_path, 'rb') as certf:
        cert_data = certf.read()

    # FIXME Hardcoded golem cli secret path
    wampcra_authid = 'golemcli'
    secret_path = '/home/mplebanski/Projects/golem/node_A/rinkeby/crossbar/secrets/golemcli.tck'

    with open(secret_path, 'rb') as secretf:
        wampcra_secret = secretf.read()

    # Mismatch golem.local - localhost
    ssl.match_hostname = lambda cert, hostname: True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cert_path)

    component = Component(
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
                u'authid': wampcra_authid,
                u'secret': wampcra_secret
            }
        },
        realm=u"golem",
    )
    return component


class GolemComponent(object):

    WAITING = 1
    STARTING = 2
    COMPUTING = 3
    FINISHED = 4
    ABORTED = 8

    def __init__(self, loop, component):
        self.loop = loop
        self.component = component
        self.q_tx = asyncio.Queue()
        self.q_rx = asyncio.Queue()

    async def map(self, methods, args):
        # Pass a method, args tuple to TX queue
        await self.q_tx.put((methods,args))

        # Get the results []
        return await self.q_rx.get()

    async def start(self):

        @self.component.on_join
        async def joined(session: Session, details: SessionDetails):
            methods, args = await self.q_tx.get()
            print('Recieved task')
            self.session = session

            futures = [
                self.compute_task(self._create_task_data(m, a)) for
                m, a in zip(methods, args)
            ]

            results = asyncio.gather(*futures)

            await self.q_rx.put(results)

        @self.component.on_disconnect
        async def disconnected(session: Session, details=None, was_clean=True):
            pass

        @self.component.on_ready
        async def ready(session: Session, details=None):
            pass

        @self.component.on_leave
        async def leave(session: Session, details=None):
            pass

        @self.component.on_connect
        async def connected(session: Session, client_protocol: WampWebSocketClientProtocol):
            pass

        f = txaio.as_future(self.component.start, self.loop)

        await asyncio.gather(f)

    def _create_task_data(self, method, args):

        method_obj = cloudpickle.dumps(method)
        args_obj = cloudpickle.dumps(args)

        return {
            'bid': 1.0,
            'resources': [
                '/home/mplebanski/Projects/golem/apps/blender/benchmark/test_task/cube.blend'
            ],
            'subtask_timeout': '00:10:00',
            'subtasks_count': 1,
            'timeout': '00:10:00',
            'type': 'Raspa',
            'extra_data': {
                'method': method_obj,
                'args': args_obj
            },
            'name': 'My task'
        }

    async def compute_task(self, task_data):
        return await self.session.call('comp.task.create', task_data)
