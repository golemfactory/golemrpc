import asyncio
import txaio

from wamp.base import wamp_register_components

txaio.use_asyncio()  # noqa

async def timer():
    while True:
        await asyncio.sleep(1.0)
        print('Hello world!') 

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    from wamp.client import component
    wamp_register_components(loop, [component])

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
