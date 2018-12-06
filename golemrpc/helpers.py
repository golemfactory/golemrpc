import appdirs
import cloudpickle
import os
import uuid

def get_golem_datadir(mainnet=False):
    """ Helper function for golem datadir
    """
    if mainnet:
        DATA_DIR = 'mainnet'
    else:
        DATA_DIR = 'rinkeby'

    return os.path.join(
        os.path.join(appdirs.user_data_dir('golem'), 'default'),
        DATA_DIR
    )


class LambdaTaskFormatter(object):
    def __init__(self, method=None, args=None, **kwargs):
        if not method or not args:
            raise ValueError('Please provide both methods and args')
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def format(self):
        d = {
            'bid': 1.0,
            'subtask_timeout': '00:10:00',
            'subtasks_count': 1,
            'timeout': '00:10:00',
            'type': 'GLambda',
            'extra_data': {
                'method': cloudpickle.dumps(self.method),
                'args': cloudpickle.dumps(self.args)
            },
            'name': 'Task {}'.format(uuid.uuid4().hex.upper()[0:6])
        }
        for k, v in self.kwargs.items():
            d[k] = v
        return d


class MultiLambdaTaskFormatter(object):
    def __init__(self, methods=None, args=None, **kwargs):
        if not methods or not args:
            raise ValueError('Please provide both methods and args')
        if type(methods) != list:
            raise ValueError('methods must be an iterable')
        if type(args) != list:
            raise ValueError('args must be an iterable')
        self.methods = methods
        self.args = args
        self.kwargs = kwargs

    def format(self):
        return [
            LambdaTaskFormatter(method=m, args=a, **self.kwargs).format() for 
            m, a in zip(self.methods, self.args) 
        ]