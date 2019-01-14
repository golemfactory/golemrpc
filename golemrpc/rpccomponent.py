import asyncio
import logging
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

signal.signal(signal.SIGINT, signal_handler)


class RPCComponent(threading.Thread):
    def __init__(self, cli_secret=None, rpc_cert=None, host='localhost', port=61000, log_level=logging.INFO):
        """A class providing communication with remote autobahn node. Works in separate thread
        and exposes a synchronous queue for message exchange with user application code.
        
        Keyword Arguments:
            cli_secret {Path} -- A path to cli_secret used to communicate with autobahn node
            rpc_cert {Path} -- A path to rpc_cert used for SSL
            host {str} -- Autobahn node hostname (default: {'localhost'})
            port {int} -- Autobahn node port (default: {61000})
            log_level {[type]} -- [description] (default: {logging.INFO})
        
        Raises:
            ValueError -- When cli_secret is not provided
            ValueError -- When rpc_cert is not provided
        """
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
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        self.handlers = {
            'rpc_call': SingleRPCCallHandler(),
            'map': TaskMapRemoteFSDecorator(TaskMapHandler()),
            'exit': RPCExitHandler(),
        }
        threading.Thread.__init__(self, daemon=True)

    def evaluate_sync(self, obj):
        """Synchronous function used for passing messages to RPC Component queue
        Arguments:
            obj {dict} -- Python dictionary of format:
            {
                "type": "message_type",
                [message specific fields]
            }
            Types: 'exit', 'rpc_call', 'map'.

            Message 'exit' will gracefully disconnnect rpc component from remote node
            {
                'type': 'exit'
            }

            Message 'rpc_call' allows to communicate with arbitrary RPC endpoint exposed
            by remote node e.g.:
            {
                'type': 'rpc_call',
                'method_name': 'task.comp.result',
                'args': []
            }

            Message 'map' allows mapping golem tasks to a set of remote
            golem nodes. Golem task is a python dictionary containing information about
            task type, timeout, price etc.
            {
                'type': 'map',
                't_dicts': [task1_dict, task2_dict]
            }
        Raises:
            results -- If an exception is thrown in rpc component thread then is it propagated
            through the message queue and reraised in application code.
        Returns:
            [list] -- List of paths containing results for each task from t_dicts (order preserved)
        """
        # FIXME For now we enforce exclusive access for input side 
        # for both queues because there is no way to distinguish actors
        # (in other words who should receive particular results if
        # results come unordered)
        self.lock.acquire()

        self.call_q.put(obj)
        results = self.response_q.get()

        self.lock.release()

        if isinstance(results, BaseException):
            raise results

        return results

    def _run(self):
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
                    obj = self.call_q.get(block=True, timeout=5.0)
                    # Handle depending on type in
                    result = await self.handlers[obj['type']](self.session, obj)
                except Exception as e:
                    self.response_q.put(e)
                else:
                    self.response_q.put(result)

        fut = asyncio.gather(
            txaio.as_future(component.start, loop)
        )
        loop.run_until_complete(fut)

    def run(self):
        # Top level exception handling layer
        # A SIGINT is sent to main thread to kill the entire process
        try:
            self._run()
        except Exception as _e:
            traceback.print_exc()
            os.kill(os.getpid(), signal.SIGINT)
