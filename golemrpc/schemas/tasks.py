import base64
import cloudpickle
import re
import uuid

from marshmallow import Schema, fields, validates

from ..core_imports import VerificationMethod


class PickledBase64PythonObjectField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return base64.b64encode(cloudpickle.dumps(value)).decode('ascii')

    def _deserialize(self, value, attr, data, **kwargs):
        return cloudpickle.loads(base64.b64decode(value))


class TaskSchema(Schema):
    bid = fields.Float(default=1.0, required=True)
    subtasks_count = fields.Int(default=1, required=True)
    subtask_timeout = fields.Str(default='00:10:00', required=True)
    timeout = fields.Str(default='00:10:00', required=True)
    task_type = fields.Str(data_key='type', required=True)
    task_name = fields.Method('get_task_name',
                              data_key='name',
                              required=True)

    resources = fields.List(fields.String())
    resources_mapped = fields.Raw(default=None)

    def get_task_name(self, obj):
        return '{}'.format(uuid.uuid1().hex.upper()[:24])

    @validates('timeout')
    @validates('subtask_timeout')
    def _timeout_validator(self, timeout):
        return re.match('[0-9][0-9]:[0-9][0-9]:[0-9][0-9]', timeout)

    @validates('task_name')
    def _name_validator(self, name):
        return len(name) <= 24


class VerificationSchema(Schema):
    verification_type = fields.Str(default=VerificationMethod.NO_VERIFICATION,
                                   required=True, data_key='type')
    method = PickledBase64PythonObjectField(default=None, allow_none=True)


class GLambdaTaskSchema(TaskSchema):
    task_type = fields.Str(required=True, data_key='type', default='Glambda')
    method = PickledBase64PythonObjectField(required=True)
    args = PickledBase64PythonObjectField(required=True, default=None, allow_none=True)
    verification = fields.Nested(VerificationSchema, default={})

    @validates('method')
    def _method_validator(self, method):
        return hasattr(method, '__call__')
