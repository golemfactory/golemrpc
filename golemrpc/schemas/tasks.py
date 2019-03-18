import base64
import re
import uuid

import cloudpickle
from marshmallow import Schema, fields, validates, post_dump

from ..core_imports import VerificationMethod


class PickledBase64PythonObjectField(fields.Field):
    """Serializing and deserializing user provided callable objects and
    their arguments. User code is serialized with cloudpickle to binary
    representation and then encoded with base64.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        return base64.b64encode(cloudpickle.dumps(value)).decode('ascii')

    def _deserialize(self, value, attr, data, **kwargs):
        return cloudpickle.loads(base64.b64decode(value))


class TaskSchema(Schema):
    """Golem task schema. User input validation and serialization.
    """

    bid = fields.Float(default=1.0, required=True)
    subtasks_count = fields.Int(default=1, required=True)
    subtask_timeout = fields.Str(default='00:10:00', required=True)
    timeout = fields.Str(default='00:10:00', required=True)
    task_type = fields.Str(attribute='type', data_key='type', required=True)
    task_name = fields.Method('get_task_name',
                              attribute='name',
                              data_key='name',
                              required=True)

    resources = fields.List(fields.String(), default=[])
    resources_mapped = fields.Raw(default={})

    def get_task_name(self, obj):
        return '{}'.format(uuid.uuid1().hex.upper()[:24])

    @validates('timeout')
    @validates('subtask_timeout')
    def _timeout_validator(self, timeout):
        return re.match('[0-9][0-9]:[0-9][0-9]:[0-9][0-9]', timeout)

    @validates('task_name')
    def _name_validator(self, name):
        return len(name) <= 24

    @post_dump(pass_original=True)
    def _add_unknown(self, data, original):
        """Add unknown fields to serialization results. There is a
        possibility that user attaches nonserializable objects 
        to schemas fields.
        """
        for key, val in original.items():
            if key not in self.fields:
                data[key] = val
        return data


class VerificationSchema(Schema):
    verification_type = fields.Str(default=VerificationMethod.NO_VERIFICATION,
                                   required=True, attribute='type',
                                   data_key='type')
    method = PickledBase64PythonObjectField(default=None, allow_none=True)


class GLambdaTaskOptions(Schema):
    method = PickledBase64PythonObjectField(required=True)
    args = PickledBase64PythonObjectField(required=True, default=None,
                                          allow_none=True)
    verification = fields.Nested(VerificationSchema, default={})
    outputs = fields.List(fields.String(),
                          default=['result.json', 'stdout.log', 'stderr.log'])
    output_path = fields.String(required=True, default='.')

    @validates('method')
    def _method_validator(self, method):
        return hasattr(method, '__call__')


class GLambdaTaskSchema(TaskSchema):
    options = fields.Nested(GLambdaTaskOptions)
