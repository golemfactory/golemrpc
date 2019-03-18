class RPCExitHandler(object):
    async def __call__(self, context, args_dict):
        context.rpc.leave()
        return {'type': 'DisconnectEvent'}
