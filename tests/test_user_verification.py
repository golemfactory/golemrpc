import asyncio
import json
import logging
import os

from golemrpc.core_imports import VerificationMethod, SubtaskVerificationState
from golemrpc.rpccomponent import RPCComponent

from utils import create_rpc_component

logging.basicConfig(level=logging.INFO)

GLAMBDA_RESULT_FILE = 'result.txt'

def load_result(results):
    f = None
    for r in results:
        if r.endswith('result.txt'):
            f = r
    return json.loads(open(f).read())


def test_successful_verification():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return 1 + 2

    response = rpc.post_wait({
        'type': 'CreateTask',
        'task':
            {
                'type': 'GLambda',
                'method': test_task,
                'verification': {
                    'type': VerificationMethod.EXTERNALLY_VERIFIED
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'VerificationRequired'
    assert response['task_id'] == task_id

    result = load_result(response['results'])
    assert result['data'] == 3
    assert 'error' not in result

    response = rpc.post_wait({
        'type': 'VerifyResults',
        'task_id': response['task_id'],
        'subtask_id': response['subtask_id'],
        'verdict': SubtaskVerificationState.VERIFIED
    })

    assert response['type'] == 'TaskResults'
    assert response['task_id'] == task_id
    result = load_result(response['results'])
    assert result['data'] == 3
    assert 'error' not in result

    rpc.post_wait({
        'type': 'Disconnect'
    })


def test_reaction_to_wrong_answer():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return 1 + 2

    response = rpc.post_wait({
        'type': 'CreateTask',
        'task':
            {
                'type': 'GLambda',
                'method': test_task,
                'verification': {
                    'type': VerificationMethod.EXTERNALLY_VERIFIED
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'VerificationRequired'
    assert response['task_id'] == task_id
    result = load_result(response['results'])
    # Intentionally do not assert 'data' field
    assert 'error' not in result

    response = rpc.post_wait({
        'type': 'VerifyResults',
        'task_id': response['task_id'],
        'subtask_id': response['subtask_id'],
        'verdict': SubtaskVerificationState.WRONG_ANSWER
    })

    assert response['type'] == 'VerificationRequired'
    assert response['task_id'] == task_id
    result = load_result(response['results'])
    assert result['data'] == 3
    assert 'error' not in result

    response = rpc.post_wait({
        'type': 'VerifyResults',
        'task_id': response['task_id'],
        'subtask_id': response['subtask_id'],
        'verdict': SubtaskVerificationState.VERIFIED
    })

    assert response['type'] == 'TaskResults'
    assert response['task_id'] == task_id

    result = load_result(response['results'])
    assert result['data'] == 3
    assert 'error' not in result

    rpc.post_wait({
        'type': 'Disconnect'
    })


def test_explicit_no_verification():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return 1 + 2

    response = rpc.post_wait({
        'type': 'CreateTask',
        'task':
            {
                'type': 'GLambda',
                'method': test_task,
                'verification': {
                    'type': VerificationMethod.NO_VERIFICATION
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'TaskResults'
    assert response['task_id'] == task_id
    result = load_result(response['results'])
    # Intentionally do not assert 'data' field
    assert 'error' not in result
    assert result['data'] == 3

    rpc.post_wait({
        'type': 'Disconnect'
    })


def test_implicit_no_verification():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return 1 + 2

    response = rpc.post_wait({
        'type': 'CreateTask',
        'task':
            {
                'type': 'GLambda',
                'method': test_task,
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'TaskResults'
    assert response['task_id'] == task_id
    result = load_result(response['results'])
    # Intentionally do not assert 'data' field
    assert 'error' not in result
    assert result['data'] == 3

    rpc.post_wait({
        'type': 'Disconnect'
    })
