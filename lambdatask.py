import cloudpickle
import uuid

from task import BaseTask

class LambdaTask(BaseTask):
    def render_task_dict(self, **app_data):
        return {
            'bid': 1.0,
            'subtask_timeout': '00:10:00',
            'subtasks_count': 1,
            'timeout': '00:10:00',
            'type': 'GLambda',
            'extra_data': {
                'method': cloudpickle.dumps(app_data['method']),
                'args': cloudpickle.dumps(app_data['args_dict'])
            },
            'name': 'Task {}'.format(uuid.uuid4().hex.upper()[0:6])
        }
