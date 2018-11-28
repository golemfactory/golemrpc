import asyncio
import logging

from client import component_get, GolemComponent

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()

        # Get default WAMP component 
        component = component_get()

        # Wrap WAMP component to support task delegation
        mycomponent = GolemComponent(loop, component)

        async def producer():
            def f(args):
                return args['val1'] + args['val2']

            args = {
                'val1': 10,
                'val2': 20
            }

            results = await mycomponent.map([f, f], [args, args])
            print(results)

        group = asyncio.gather(
            mycomponent.start(),
            producer()
        )

        loop.run_until_complete(group)
    except Exception as e:
        logging.exception('')
        print(e)