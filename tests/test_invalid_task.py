import asyncio
import json
import os

from utils import create_rpc_component

# TODO move to test framework

GLAMBDA_RESULT_FILE = 'result.txt'


def test_raise_exception():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        raise RuntimeError(TEST_STRING)

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': test_task,
        }
    })

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        result_json = json.loads(f.read())
    assert 'error' in result_json
    assert result_json['error'] == TEST_STRING
    assert 'data' not in result_json

    rpc.post_wait({
        'type': 'Disconnect'
    })


def test_empty_resource():
    rpc = create_rpc_component()
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        pass

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': test_task
        }
    })

    results = rpc.poll(timeout=None)['results']

    assert set(results) == expected_results
    result_directory = os.path.split(results[0])[0]

    rpc.post_wait({
        'type': 'Disconnect'
    })


def test_invalid_resource():
    rpc = create_rpc_component()
    rpc.start()
    # FIXME remove this ugly exception assertion when moving to test framework

    def test_task(args):
        pass
    try:
        rpc.post_wait({
            'type': 'CreateTask',
            'task': {
                'method': test_task,
            }
        })['results']
    except:
        pass
    else:
        assert False


def test_task_timeout():
    rpc = create_rpc_component()
    rpc.start()
    # FIXME remove exception assertion when moving to test framework

    def test_task(args):
        import time
        time.sleep(5.0)
    try:
        _ = rpc.post_wait({
            'type': 'CreateTask',
            'task': {
                'type': 'GLambda',
                'method': test_task,
                'timeout': '00:00:00'
            }
        })
        rpc.poll(timeout=None)
    except RuntimeError as e:
        pass
    else:
        assert False


def test_task_too_big():
    rpc = create_rpc_component()
    rpc.start()
    # FIXME remove exception assertion when moving to test framework

    def test_task(args):
        import time
        time.sleep(5.0)
    try:
        _ = rpc.post_wait({
            'type': 'CreateTask',
            'task': {
                'type': 'GLambda',
                'method': test_task,
                'timeout': '00:00:00',
                'dummy_data': [0 for _ in range(10*1024*1024)]
            }
        })
        rpc.poll(timeout=None)
    except ValueError as e:
        pass
    else:
        assert False


def test_task_non_serializable():
    rpc = create_rpc_component()
    rpc.start()
    # FIXME remove exception assertion when moving to test framework

    def test_task(args):
        import time
        time.sleep(5.0)
    try:
        _ = rpc.post_wait({
            'type': 'CreateTask',
            'task': {
                'type': 'GLambda',
                'method': test_task,
                'timeout': '00:00:00',
                'dummy_data': lambda x: print(x)
            }
        })
        rpc.poll(timeout=None)
    except RuntimeError as e:
        pass
    else:
        assert False
