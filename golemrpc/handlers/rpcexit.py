from autobahn.asyncio.wamp import Session


class RPCExitHandler(object):
    async def __call__(self, context, args_dict):
        session = context.session
        session.leave()
        return {'msg': 'Successfully disconnected'}