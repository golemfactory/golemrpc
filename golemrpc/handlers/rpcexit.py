from autobahn.asyncio.wamp import Session


class RPCExitHandler(object):
    async def __call__(self, session: Session, args_dict):
        session.leave()
        return {'msg': 'Successfully disconnected'}