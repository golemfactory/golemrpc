import asyncio
import json
import os

from utils import create_controller

# TODO move to test framework

GLAMBDA_RESULT_FILE = 'result.txt'


def test_raise_exception():
    controller = create_controller()
    controller.start()

    TEST_STRING = 'test'
    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log']

    def test_task(args):
        raise RuntimeError(TEST_STRING)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert os.listdir(result_directory) == expected_results
    assert all(f in expected_results for f in os.listdir(result_directory))
    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        result_json = json.loads(f.read())
    assert 'error' in result_json
    assert result_json['error'] == TEST_STRING
    assert 'data' not in result_json

    controller.stop()


def test_empty_resource():
    controller = create_controller()
    controller.start()

    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log']

    def test_task(args):
        pass

    results = controller.map(
        methods=[test_task],
        args=[{}],
        resources=[]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert os.listdir(result_directory) == expected_results
    assert all(f in expected_results for f in os.listdir(result_directory))

    controller.stop()


def test_invalid_resource():
    controller = create_controller()
    controller.start()
    # FIXME remove this ugly exception assertion when moving to test framework

    def test_task(args):
        pass
    try:
        controller.map(
            methods=[test_task],
            args=[{}],
            resources=['test-aaaaaaaaaaaaaaaaaa']
        )
    except:
        pass
    else:
        assert False


def test_task_timeout():
    controller = create_controller()
    controller.start()
    # FIXME remove exception assertion when moving to test framework

    def test_task(args):
        import time
        time.sleep(5.0)
    try:
        results = controller.map(
            methods=[test_task],
            args=[{}],
            timeout='00:00:00'
        )
    except BaseException as e:
        pass
    else:
        assert False
