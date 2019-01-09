from autobahn.asyncio.wamp import Session

class RPCExitHandler(object):
    def __init__(self, logger):
        self.logger = logger
    async def __call__(self, session: Session, args_dict):
        session.leave()
        return {'msg': 'Successfully disconnected'}