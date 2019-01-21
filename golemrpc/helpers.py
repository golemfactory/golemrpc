import appdirs
import base64
import cloudpickle
import os
import uuid


class LambdaTaskFormatter(object):
    def __init__(self, method=None, args=None, **kwargs):
        assert method is not None
        assert args is not None
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
                'method': base64.b64encode(cloudpickle.dumps(self.method)).decode('ascii'),
                'args': base64.b64encode(cloudpickle.dumps(self.args)).decode('ascii')
            },
            'name': 'Task {}'.format(uuid.uuid4().hex.upper()[0:6])
        }
        for k, v in self.kwargs.items():
            d[k] = v
        return d


class TaskMapFormatter(object):
    def __init__(self, methods=None, args=None, **kwargs):
        assert type(methods) == list
        assert type(args) == list
        self.methods = methods
        self.args = args
        self.kwargs = kwargs

    def format(self):
        return [
            LambdaTaskFormatter(method=m, args=a, **self.kwargs).format()
            for m, a in zip(self.methods, self.args) 
        ]
