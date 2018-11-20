from autobahn.asyncio.component import Component
from autobahn.asyncio.wamp import ApplicationSession
from twisted.internet._sslverify import optionsForClientTLS  # noqa # pylint: disable=protected-access
from twisted.internet import reactor
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet.defer import inlineCallbacks, Deferred

import asyncio
from functools import partial
import signal
import ssl
import txaio

txaio.use_asyncio()  # noqa

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

def run(components, log_level='info'):
    if log_level is not None:
        txaio.start_logging(level=log_level)
    loop = asyncio.get_event_loop()
    log = txaio.make_logger()

    # Code taken from autobahn.wamp.component
    def reactor_add_components(reactor, components):
        def component_success(comp, arg):
            log.debug("Component '{c}' successfully completed: {arg}", c=comp, arg=arg)
            return arg

        def component_failure(comp, f):
            log.error("Component '{c}' error: {msg}", c=comp, msg=txaio.failure_message(f))
            log.debug("Component error: {tb}", tb=txaio.failure_format_traceback(f))
            return None

        def component_start(comp):
            d = txaio.as_future(comp.start, reactor)
            txaio.add_callbacks(
                d,
                partial(component_success, comp),
                partial(component_failure, comp),
            )
            return d

        done_d = txaio.gather([component_start(c) for c in components], consume_exceptions=False)

        def all_done(arg):
            log.debug("All components ended; stopping reactor")
            if isinstance(arg, Failure):
                log.error("Something went wrong: {log_failure}", failure=arg)
            try:
                reactor.stop()
            except ReactorNotRunning:
                pass
        txaio.add_callbacks(done_d, all_done, all_done)
        return done_d

    def reactor_add_signal_handling(reactor):
        @asyncio.coroutine
        def exit():
            return reactor.stop()

        def nicely_exit(signal):
            log.info("Shutting down due to {signal}", signal=signal)
            for task in asyncio.Task.all_tasks():
                task.cancel()
            asyncio.ensure_future(exit())

        reactor.add_signal_handler(signal.SIGINT, partial(nicely_exit, 'SIGINT'))
        reactor.add_signal_handler(signal.SIGTERM, partial(nicely_exit, 'SIGTERM'))

    reactor_add_signal_handling(loop)
    reactor_add_components(loop, components)

    async def timer():
        while True:
            await asyncio.sleep(1.0)
            print('Hello world!') 

    d = txaio.as_future(timer)
    txaio.add_callbacks(
        d, 
        lambda success: print('success: ' + str(success)),
        lambda error: print('error: ' + str(error)),
    )

    try:
        loop.run_forever()
    except asyncio.CancelledError:
        pass
    loop.close()

if __name__ == "__main__":
    run([comp])
