from .helpers import TaskMapFormatter

class RPCController(object):
    def __init__(self, rpc_component):
        self.rpc_component = rpc_component

    def map(self, methods=None, args=None):
        # Formatting methods and args for golem rpc component
        formatter = TaskMapFormatter(
            methods=methods,
            args=args
        )
        return self.rpc_component.evaluate_sync({
            'type': 'map',
            't_dicts': formatter.format()
        })

    def stop(self):
        return self.evaluate_sync({
            'type': 'exit'
        })
