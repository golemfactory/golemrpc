from autobahn.asyncio.wamp import Session

class SingleRPCCallHandler(object):
    async def __call__(self, session: Session, args_dict):
        method_name = args_dict['method_name']
        args = args_dict['args']
        return await session.call(method_name, *args)