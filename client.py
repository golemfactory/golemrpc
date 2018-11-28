from autobahn.asyncio.component import Component
from autobahn.asyncio.websocket import WampWebSocketClientProtocol
from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

import asyncio
import cloudpickle
import json
import logging
import ssl
import txaio

from core_imports import TaskOp

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

    def __init__(self, loop, component):
        self.loop = loop
        self.component = component
        self.q_tx = asyncio.Queue()
        self.q_rx = asyncio.Queue()
        self.event_arr = []

    async def map(self, methods, args):
        # Pass a method, args tuple to TX queue
        await self.q_tx.put((methods,args))

        # Get the results []
        return await self.q_rx.get()

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))

    async def collect_task(self, task_id):
        # Active polling
        # Not optimal but trivial
        related_evts = []

        while True:
            await asyncio.sleep(1.0)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == task_id, self.event_arr))

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        state = await self.session.call('comp.task.state', task_id)
        results = state['subtask_states'].popitem()[1]['results']

        print(results)

        return 'Dummy finish'

    async def on_task_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        self.event_arr.append(
            (task_id, subtask_id, TaskOp(op_value))
        )

    async def start(self):
        @self.component.on_join
        async def joined(session: Session, details: SessionDetails):
            while True:
                methods, args = await self.q_tx.get()
                self.session = session

                futures = [
                    self.compute_task(self._create_task_data(m, a)) for
                    m, a in zip(methods, args)
                ]

                create_results = await asyncio.gather(*futures)

                if any(error_message for _, error_message in create_results):
                    # Some tasks failed to created, abort all
                    futures = [
                        session.call('comp.task.abort', task_id) for
                        task_id, _ in create_results
                    ]

                    # Await for all aborts to complete
                    await asyncio.gather(futures)

                    raise RuntimeError('Failed to create tasks: ' + create_results)

                # Subscribe for updates before sending create requests
                await session.subscribe(self.on_task_status_update,
                    u'evt.comp.task.status')

                futures = [
                    self.collect_task(task_id) for 
                    task_id, error_message in create_results
                ]

                results = await asyncio.gather(*futures)

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
    
    async def stop(self):
        self.session.leave()    

    def _create_task_data(self, method, args):

        method_obj = cloudpickle.dumps(method)
        args_obj = cloudpickle.dumps(args)
        t_dict = {
            'type': "Blender",
            'name': 'test task',
            'timeout': "0:10:00",
            "subtask_timeout": "0:09:50",
            "subtasks_count": 1,
            "bid": 1.0,
            "resources": ['/home/mplebanski/Projects/golem/apps/blender/benchmark/test_task/cube.blend'],
            "options": {
                "output_path": '/home/mplebanski/Documents',
                "format": "PNG",
                "resolution": [
                    320,
                    240
                ]
            }
        }

        return t_dict

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
