import asyncio
import logging

from base import component_get, GolemComponent

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()

        component = component_get()

        mycomponent = GolemComponent(loop, component)

        async def producer():
            def f(args):
                return args['val1'] + args['val2']

            args = {
                'val1': 10,
                'val2': 20
            }
            print('Asigning task')
            await mycomponent.q_tx.put([[f], [args]])

        group = asyncio.gather(
            mycomponent.start(),
            producer()
        )

        loop.run_until_complete(group)
    except Exception as e:
        logging.exception('')
        print(e)