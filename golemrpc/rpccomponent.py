import asyncio
import functools
import logging
import os
import queue
import signal
import threading
import traceback

import janus
import txaio
from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

from .handlers.rpcexit import RPCExitHandler
from .handlers.singlerpc import SingleRPCCallHandler
from .handlers.task_controller import TaskController
from .utils import create_component


class ExitCommand(Exception):
    pass


def signal_handler(signal, frame):
    raise ExitCommand()


signal.signal(signal.SIGINT, signal_handler)


def alive_required(func):
    """Make sure thread is running before proceeding"""

    @functools.wraps(func)
    def wrapper_alive_required(self, *args, **kwargs):
        if not self.is_alive():
            raise RuntimeError('Component has not been started. You must\
                first run .start() method on rpc component')
        return func(self, *args, **kwargs)

    return wrapper_alive_required


class RPCComponent(threading.Thread):
    def __init__(self, cli_secret_filepath=None, rpc_cert_filepath=None,
                 host='localhost', port=61000, log_level=logging.INFO,
                 timeout=3.0, remote=True):
        """Provides communication with remote Golem node.
        Works in separate thread and exposes a queue for message
        exchange with user application code.

        Keyword Arguments:
            cli_secret_filepath {Path} -- A path to cli_secret_filepath used to communicate with autobahn node
            rpc_cert_filepath {Path} -- A path to rpc_cert_filepath used for SSL
            host {str} -- Autobahn node hostname (default: {'localhost'})
            port {int} -- Autobahn node port (default: {61000})
            log_level {[type]} -- [description] (default: {logging.INFO})
            timeout {float} -- time after which RPC component will send TimeoutError exception
            remote {boolean} -- flag informing if Golem node is remote or local to the application

        Raises:
            ValueError -- When cli_secret_filepath is not provided
            ValueError -- When rpc_cert_filepath is not provided
        """
        if not cli_secret_filepath:
            raise ValueError("Provide cli_secret_filepath")
        if not rpc_cert_filepath:
            raise ValueError("Provide rpc_cert_filepath")
        self.cli_secret_filepath = cli_secret_filepath
        self.rpc_cert_filepath = rpc_cert_filepath
        self.host = host
        self.port = port
        # Cross thread communication queue
        self.lock = threading.Lock()
        self.call_q = None
        self.response_q = None
        self.rpc = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        self.task_controller = TaskController()
        self.handlers = {
            'RPCCall': SingleRPCCallHandler(),
            'CreateTask': self.task_controller,
            'VerifyResults': self.task_controller,
            'Disconnect': RPCExitHandler()
        }
        self.loop = asyncio.new_event_loop()
        self.call_q = janus.Queue(loop=self.loop)
        self.response_q = janus.Queue(loop=self.loop)
        self.component = create_component(
            cli_secret_filepath=self.cli_secret_filepath,
            rpc_cert_filepath=self.rpc_cert_filepath,
            host=self.host,
            port=self.port
        )
        self.joined = False
        self.timeout = timeout
        self.remote = remote
        threading.Thread.__init__(self, daemon=True)

    @alive_required
    def post_wait(self, obj):
        response = None
        with self.lock:
            self.call_q.sync_q.put(obj)
            response = self.response_q.sync_q.get()
            if isinstance(response, BaseException):
                raise response
        return response

    @alive_required
    def post(self, obj, block=True, timeout=1.0):
        with self.lock:
            self.call_q.sync_q.put(obj, block=block, timeout=timeout)

    @alive_required
    def poll(self, block=True, timeout=1.0):
        response = None
        with self.lock:
            response = self.response_q.sync_q.get(block=block, timeout=timeout)
            if isinstance(response, BaseException):
                raise response
        return response

    def _run(self):
        txaio.config.loop = self.loop
        asyncio.set_event_loop(self.loop)

        # It's a new thread, we create a new event loop for it.
        # Not doing so and using default loop might break
        # library's user code.

        @self.component.on_join
        async def joined(session: Session, details: SessionDetails):
            self.joined = True
            self.rpc = session
            while True:
                try:
                    message = await self.call_q.async_q.get()

                    # NOTE now if we pass context (self) to handler and it decides to
                    # send a result using context.response_q we have multiple
                    # ways to send back responses which is bad.
                    # Passing context to handlers gives flexibility but enables
                    # arbitrary side effects from handlers.

                    # Handle depending on message type
                    response = await self.handlers[message['type']](self,
                                                                    message)
                except queue.Empty:
                    pass
                except Exception as e:
                    self.response_q.sync_q.put(e)
                else:
                    if response:
                        self.response_q.sync_q.put(response)

        asyncio.ensure_future(self._watchdog(self.timeout))
        asyncio.ensure_future(txaio.as_future(self.component.start, self.loop))
        self.loop.run_forever()

    async def _watchdog(self, timeout):
        await asyncio.sleep(timeout)
        if self.joined:
            pass
        else:
            self.response_q.sync_q.put(
                RuntimeError('Connection attempt failed'))

    def run(self):
        # Top level exception handling layer
        # A SIGINT is sent to main thread to kill the entire process
        try:
            self._run()
        except Exception as _e:
            traceback.print_exc()
            os.kill(os.getpid(), signal.SIGINT)
