class SingleRPCCallHandler(object):
    async def __call__(self, context, args_dict):
        method_name = args_dict['method_name']
        args = args_dict['args']
        return await context.rpc.call(method_name, *args)
