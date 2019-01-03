import asyncio 
import os
import queue
import signal
import sys
import threading
import traceback
import txaio

from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

from .utils import create_component
from .handlers.singlerpc import SingleRPCCallHandler
from .handlers.taskmap import TaskMapHandler, TaskMapRemoteFSDecorator
from .handlers.rpcexit import RPCExitHandler

class ExitCommand(Exception):
    pass

def signal_handler(signal, frame):
    raise ExitCommand()

signal.signal(signal.SIGUSR1, signal_handler)

class RPCComponent(threading.Thread):
    def __init__(self, cli_secret=None, rpc_cert=None, host='localhost', port=61000):
        if not cli_secret:
            raise ValueError("Provide cli_secret")
        if not rpc_cert:
            raise ValueError("Provide rpc_cert")
        self.cli_secret = cli_secret
        self.rpc_cert = rpc_cert
        self.host = host
        self.port = port
        # Cross thread communication queue
        self.lock = threading.Lock()
        self.call_q = queue.Queue()
        self.response_q = queue.Queue()
        self.event_q = queue.Queue(maxsize=16)
        self.session = None
        self.handlers = {
            'rpc_call': SingleRPCCallHandler(),
            'map': TaskMapRemoteFSDecorator(TaskMapHandler()),
            'exit': RPCExitHandler(),
        }
        threading.Thread.__init__(self, daemon=True)

    def evaluate_sync(self, obj):
        # FIXME For now we enforce exclusive access for input side 
        # for both queues because there is no way to distinguish actors
        # (in other words who should receive particular results if
        # results come unordered)
        self.lock.acquire()

        self.call_q.put(obj)
        results = self.response_q.get()

        self.lock.release()

        return results

    def run(self):
        component = create_component(
            cli_secret=self.cli_secret,
            rpc_cert=self.rpc_cert,
            host=self.host,
            port=self.port
        )
        loop = asyncio.new_event_loop()

        txaio.config.loop = loop
        asyncio.set_event_loop(loop)

        @component.on_join
        async def joined(session: Session, details: SessionDetails):
            self.session = session
            while True:
                try:
                    obj = self.call_q.get(block=False)
                    # Handle depending on type in
                    result = await self.handlers[obj['type']](self.session, obj)
                except queue.Empty as e:
                    await asyncio.sleep(1.0)
                except Exception as e:
                    traceback.print_exc()
                    os.kill(os.getpid(), signal.SIGUSR1)
                else:
                    self.response_q.put(result)

        fut =  asyncio.gather(
            txaio.as_future(component.start, loop)
        )
        try:
            loop.run_until_complete(fut)
        except Exception as e:
            traceback.print_exc()
            print(e)
            os.kill(os.getpid(), signal.SIGUSR1)
