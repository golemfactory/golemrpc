# Messages

### Format 

Every message contains field:

- type: (string, required) - that describes the message type

## CreateTask

Message used to create a task on a remote Golem node.

### Format

- task: (object, required) 
    - bid: (float, required, default=1.0) 
    - subtasks_count: (integer, required, default=1) 
    - subtask_timeout: (string, required, default='00:10:00) 
    - timeout: (string, required, default='00:10:00) 
    - type: (string, required)
    - task_name: (string, required, default=${uuid1[:24]})
    - resources: (list[string], required, default=[])
    - resources_mapped: (map{string,string}, required, default={}) - NOTE: remote Golem only
    - task specific fields

where `VerificationMethod` is defined as:

```python
class VerificationMethod():
    NO_VERIFICATION = "None"
    EXTERNALLY_VERIFIED = "External"
```

Every additional provided field that is not in schema will be included as is. It must be serializable, otherwise
a `RuntimeError` will be thrown.

### Example message

```json
{
    "type": "CreateTask",
    "task": {
        "type": "Blender",
        "bid": 1.0,
        "subtask_timeout": "00:10:00",
        "timeout": "00:10:00",
        "name": "my_task_0",
        "subtasks_count": 4,
        "resources": [
            "/home/user/bmw27_cpu.blend"
        ],
        "options": {
            "output_path": "/home/user",
            "format": "PNG",
            "resolution": [
                400,
                300
            ]
        }
    }
}
```

## VerifyResults

**This message is only supported by GLambda type of task**

Message used to verify subtask's results. This is experimental implementation of  "User-side verification" in Golem.

### Format

- task_id: (string, required) - identifies task for which a subtask verdict is sent
- subtask_id: (string, required) - identifies subtask for which verdict is sent
- verdict: (integer, required) - verification verdict


where verdict is a `SubtaskVerificationState` defined as:

```python
class SubtaskVerificationState(IntEnum):
    UNKNOWN_SUBTASK = 0
    WAITING = 1
    IN_PROGRESS = 2
    VERIFIED = 3
    WRONG_ANSWER = 4
    NOT_SURE = 5
    TIMEOUT = 6
```

For now only `VERIFIED` and `WRONG_ANSWER` are in used and working.

### Example message
```json
{
    "type": "VerifyResults",
    "task_id": response["task_id"],
    "subtask_id": response["subtask_id"],
    "verdict": SubtaskVerificationState.VERIFIED
}
```

# Responses 

### Format

Every response contains field:

- type: (string, required) - that describes the message type

## TaskCreatedEvent

Event informing about task creation. Fields:

### Format

- task_id: (string) - Task identifier assigned to created task
- task: (object) - task object passed to `CreateTask` message

### Example message

```json
{
    "type": "TaskCreatedEvent",
    "task_id": "cbc0b540-3c06-11e9-b806-",
    "task": { ... }
}
```

## TaskResults

Event informing about task creation. Fields:

### Format

- task_id: (string) - Task identifier 
- task: (object) - task object passed to `CreateTask` message
- results: (list[string]) - list of paths to task results

### Example message
```json
{
    "type": "TaskResults",
    "task_id": "cbc0b540-3c06-11e9-b806-",
    "results": ["/home/user/result.json", "/home/user/stdout.log"],
    "task": { ... }
}
```

## VerificationRequired

**This message is only supported by GLambda type of task**

Event informing about subtask requiring user-side verification. Fields:

### Format

- task_id: (string) - Task identifier 
- subtask_id: (string) - Subtask identifier 
- task: (object) - task object passed to `CreateTask` message
- results: (list[string]) - list of paths to task results

### Example message
```json
{
    "type": "VerificationRequired",
    "task_id": "cbc0b540-3c06-11e9-b806-",
    "subtask_id": "cbc0b540-3cff-11e9-b806-",
    "results": ["/home/user/result.json", "/home/user/stdout.log"],
    "task": { ... }
}
```
