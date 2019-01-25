from .helpers import TaskMapFormatter


class RPCController(object):
    def __init__(self, rpc_component):
        """
        Arguments:
            rpc_component {golemrpc.RPCComponent} -- Golem RPC Component
        """
        self.rpc_component = rpc_component

    def map(self, methods=None, args=None, **kwargs):
        """Maps a list of methods and corresponding args to t_dicts (see doc for RPCComponent)
        and puts them in component message queue for evaluation. Basically this is a helpers function
        allowing users to work directly with their function objects and arguments instead of
        library specific data formats.

        Keyword Arguments:
            methods {[list]} -- List of function objects to post (default: {None})
            args {[type]} -- List of arguments corresponding to function objects in methods args  (default: {None})

        Returns:
            [list] -- List of paths containing results for function object (order preserved)
        """
        # Formatting methods and args for golem rpc component
        assert len(methods) == len(args)
        formatter = TaskMapFormatter(
            methods=methods,
            args=args,
            **kwargs
        )
        return self.rpc_component.post_wait({
            'type': 'map',
            't_dicts': formatter.format()
        })

    def start(self):
        """Start RPC Component thread.
        """
        self.rpc_component.start()

    def stop(self):
        """Stop RPC Component thread
        """
        return self.rpc_component.post_wait({
            'type': 'exit'
        })
