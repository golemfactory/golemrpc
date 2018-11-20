from autobahn.asyncio.component import Component

import asyncio
import json
import ssl
import txaio

log = txaio.make_logger()

# FIXME Hardcoded golem node_A cert 
cert_path = '/home/mplebanski/Projects/golem/node_A/rinkeby/crossbar/rpc_cert.pem'

with open(cert_path, 'rb') as f:
    cert_data = f.read()

# FIXME Hardcoded golem cli secret path
wampcra_authid = 'golemcli'
secret_path = '/home/mplebanski/Projects/golem/node_A/rinkeby/crossbar/secrets/golemcli.tck'

with open(secret_path, 'rb') as f:
    wampcra_secret = f.read()

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
    import pickle
    import base64
    # import golem.client
    # golem.client.create_task


    method_obj = pickle.dumps(method)
    args_obj = pickle.dumps(args)

    return {
        'bid': 5.0, 
         'resources': [
             '/home/mplebanski/Projects/golem/apps/blender/benchmark/test_task/cube.blend'
         ],
         'subtask_timeout': '00:10:00',
         'subtasks': 1,
         'timeout': '00:10:00',
         'type': 'Raspa',
         'extra_data': {
             'method': base64.encodebytes(method_obj).decode('ascii'),
             'args': base64.encodebytes(args_obj).decode('ascii')
         },
         'name': 'My task'
     }

mof = {
    'a': 10,
    'b': 15
}

def f(*args):
    return sum(*args)

@component.on_join
async def joined(session: Session, details: SessionDetails):

    await session.subscribe(lambda status: print('status ' + str(status)),
                            u'evt.golem.status')
    await session.subscribe(lambda task_id, subtask_id, op_value: print('task status ' + str(op_value)),
                            u'evt.comp.task.status')
    await session.subscribe(lambda task_id, subtask_id, op_value: print('subtask status ' + str(op_value)),
                            u'evt.comp.subtask.status')
    await session.subscribe(lambda node_id, task_id, reason, details: print('task.prov_rejected ' + str(reason)),
                            u'evt.comp.task.prov_rejected')


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