import json
import logging

from utils import create_rpc_component

from golemrpc.core_imports import VerificationMethod, SubtaskVerificationState

logging.basicConfig(level=logging.INFO)

GLAMBDA_RESULT_FILE = 'result.json'


def load_result(results):
    f = None
    for r in results:
        if r.endswith(GLAMBDA_RESULT_FILE):
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
                'options': {
                    'method': test_task,
                    'verification': {
                        'type': VerificationMethod.EXTERNALLY_VERIFIED
                    }
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'TaskAppData'
    assert response['app_data']['type'] == 'SubtaskCreatedEvent'

    response = rpc.poll(timeout=None)
    assert response['type'] == 'TaskAppData'
    assert response['app_data']['type'] == 'VerificationRequest'

    result = load_result(response['app_data']['results'])
    assert result['data'] == 3
    assert 'error' not in result

    response = rpc.post_wait({
        'type': 'VerifyResults',
        'task_id': response['task_id'],
        'subtask_id': response['app_data']['subtask_id'],
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
                'options': {
                    'method': test_task,
                    'verification': {
                        'type': VerificationMethod.EXTERNALLY_VERIFIED
                    }
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['app_data']['type'] == 'SubtaskCreatedEvent'
    assert response['task_id'] == task_id

    response = rpc.poll(timeout=None)
    assert response['app_data']['type'] == 'VerificationRequest'
    assert response['task_id'] == task_id
    result = load_result(response['app_data']['results'])
    # Intentionally do not assert 'data' field
    assert 'error' not in result

    response = rpc.post_wait({
        'type': 'VerifyResults',
        'task_id': response['task_id'],
        'subtask_id': response['app_data']['subtask_id'],
        'verdict': SubtaskVerificationState.WRONG_ANSWER
    })

    response = rpc.poll(timeout=None)
    assert response['app_data']['type'] == 'VerificationRequest'
    assert response['task_id'] == task_id
    result = load_result(response['app_data']['results'])
    assert result['data'] == 3
    assert 'error' not in result

    response = rpc.post_wait({
        'type': 'VerifyResults',
        'task_id': response['task_id'],
        'subtask_id': response['app_data']['subtask_id'],
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
                'options': {
                    'method': test_task,
                    'verification': {
                        'type': VerificationMethod.NO_VERIFICATION
                    }
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'TaskAppData'
    assert response['app_data']['type'] == 'SubtaskCreatedEvent'

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
                'options': {
                    'method': test_task
                }
            }
    })

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    response = rpc.poll(timeout=None)
    assert response['type'] == 'TaskAppData'
    assert response['task_id'] == task_id
    assert response['app_data']['type'] == 'SubtaskCreatedEvent'

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


def test_task_group_verification():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return args['a'] + args['b']

    response = rpc.post_wait({
        'type': 'CreateTask',
        'task':
            {
                'type': 'GLambda',
                'subtasks_count': 4,
                'options': {
                    'method': test_task,
                    'args': [
                        {'a': 1, 'b': 2},
                        {'a': 3, 'b': 4},
                        {'a': 5, 'b': 6},
                        {'a': 7, 'b': 8}
                    ],
                    'verification': {
                        'type': VerificationMethod.EXTERNALLY_VERIFIED
                    }

                }
            }
    })

    expected_results = [
        3,
        7, 
        11, 
        15
    ]

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    subtask_created_evt_count = 0
    subtask_verified_count = 0
    subtask_id_to_user_arguments_mapping = {}

    response = rpc.poll(timeout=None)

    while response['type'] != 'TaskResults':
        if response['type'] == 'TaskAppData':
            app_data = response['app_data']

            if app_data['type'] == 'SubtaskCreatedEvent':
                subtask_created_evt_count += 1
                subtask_id_to_user_arguments_mapping[app_data['subtask_id']] = app_data['subtask_seq_index']

            elif app_data['type'] == 'VerificationRequest':
                expected_result_id = subtask_id_to_user_arguments_mapping[app_data['subtask_id']]
                assert expected_results[expected_result_id] == load_result(app_data['results'])['data']
                rpc.post({
                    'type': 'VerifyResults',
                    'task_id': response['task_id'],
                    'subtask_id': app_data['subtask_id'],
                    'verdict': SubtaskVerificationState.VERIFIED
                })
                subtask_verified_count += 1
        response = rpc.poll(timeout=None)

    assert subtask_created_evt_count == len(expected_results)
    assert subtask_verified_count == len(expected_results)

    rpc.post_wait({
        'type': 'Disconnect'
    })


def test_task_group_verification_with_recomputation():
    rpc = create_rpc_component()
    rpc.start()

    TEST_STRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return args['a'] + args['b']

    response = rpc.post_wait({
        'type': 'CreateTask',
        'task':
            {
                'type': 'GLambda',
                'subtasks_count': 4,
                'options': {
                    'method': test_task,
                    'args': [
                        {'a': 1, 'b': 2},
                        {'a': 3, 'b': 4},
                        {'a': 5, 'b': 6},
                        {'a': 7, 'b': 8}
                    ],
                    'verification': {
                        'type': VerificationMethod.EXTERNALLY_VERIFIED
                    }
                }
            }
    })

    expected_results = [
        3,
        7, 
        11, 
        15
    ]

    assert response['type'] == 'TaskCreatedEvent'
    task_id = response['task_id']

    subtask_created_evt_count = 0
    subtask_verified_count = 0
    subtask_id_to_user_arguments_mapping = {}

    response = rpc.poll(timeout=None)

    while response['type'] != 'TaskResults':
        if response['type'] == 'TaskAppData':
            app_data = response['app_data']

            if app_data['type'] == 'SubtaskCreatedEvent':
                subtask_created_evt_count += 1
                subtask_id_to_user_arguments_mapping[app_data['subtask_id']] = app_data['subtask_seq_index']

            elif app_data['type'] == 'VerificationRequest':
                expected_result_id = subtask_id_to_user_arguments_mapping[app_data['subtask_id']]
                assert expected_results[expected_result_id] == load_result(app_data['results'])['data']

                verdict = SubtaskVerificationState.VERIFIED

                # Emulate subtask failure
                if subtask_verified_count == 2:
                    verdict = SubtaskVerificationState.WRONG_ANSWER

                rpc.post({
                    'type': 'VerifyResults',
                    'task_id': response['task_id'],
                    'subtask_id': app_data['subtask_id'],
                    'verdict': verdict
                })
                subtask_verified_count += 1
        response = rpc.poll(timeout=None)

    assert subtask_created_evt_count == len(expected_results) + 1
    # Include subtask failure emulation
    assert subtask_verified_count == len(expected_results) + 1

    rpc.post_wait({
        'type': 'Disconnect'
    })
