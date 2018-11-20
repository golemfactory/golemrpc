import asyncio
import txaio

from wamp.base import wamp_register_components

txaio.use_asyncio()  # noqa

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    from wamp.client import component
    wamp_register_components(loop, [component])

    try:
        loop.run_forever()
    except asyncio.CancelledError:
        pass
    loop.close()
