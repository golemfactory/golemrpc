import asyncio
from functools import partial
import signal
import ssl
import txaio

def wamp_register_components(loop, components, log_level='info'):
    if log_level is not None:
        txaio.start_logging(level=log_level)
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