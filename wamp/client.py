from autobahn.asyncio.component import Component

import asyncio
import json
import ssl
import txaio
import cloudpickle
import time

log = txaio.make_logger()

# FIXME Hardcoded golem node_A cert
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

from autobahn.asyncio.websocket import WampWebSocketClientProtocol
from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

def get_task_data(method, args):

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


@component.on_join
async def joined(session: Session, details: SessionDetails):

    async def on_task_status_update(task_id, subtask_id, op_value):
        FINISHED = 4
        if op_value == FINISHED:
            print('task status task_id: ' + str(task_id))
            print('calling comp.task.state with {}'.format(task_id))
            obj = await session.call('comp.task.state', task_id)

            if not obj:
                raise RuntimeError('Failed to create task: ' + error_message)

            print(obj)
            session.leave()

    await session.subscribe(on_task_status_update, u'evt.comp.task.status')

    mof = {
        'a': 10,
        'b': 15
    }

    def f(args):
        time.sleep(7.5)
        return args['a'] + args['b']

    task_data = get_task_data(f, mof)

    (task_id, error_message) = await session.call('comp.task.create', task_data)
    if not task_id:
        raise RuntimeError('Failed to create task: ' + error_message)

    log.info('Task {task_id} created', task_id=task_id)

@component.on_connect
async def connected(session: Session, client_protocol: WampWebSocketClientProtocol):
    pass

@component.on_disconnect
async def disconnected(session: Session, details=None, was_clean=True):
    pass

@component.on_ready
async def ready(session: Session, details=None):
    pass

@component.on_leave
async def leave(session: Session, details=None):
    pass
