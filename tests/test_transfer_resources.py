import asyncio
import json
import os

from utils import create_controller

# TODO move to test framework

GLAMBDA_RESULT_FILE = 'result.txt'

def test_no_output():
    controller = create_controller()
    controller.start()

    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log']
    def test_task(args):
        pass

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert os.listdir(result_directory) == expected_results
    assert all(f in expected_results for f in os.listdir(result_directory))
    controller.stop()

def test_big_file_output():
    controller = create_controller()
    controller.start()

    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log', 'result.bin']
    FILE_SIZE=50*1024*1024
    TESTBYTE = b'\xDA'
    def test_task(args):
        with open('/golem/output/result.bin', 'wb') as f:
            # Could use os.truncate but result is platform dependent
            # if the resulting file is bigger than before truncation
            # which is the case here 
            for _ in range(FILE_SIZE):
                f.write(TESTBYTE)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert all(f in expected_results for f in os.listdir(result_directory))
    assert os.stat(
        os.path.join(result_directory, 'result.bin')
    ).st_size == FILE_SIZE
    controller.stop()

def test_task_result_output():
    controller = create_controller()
    controller.start()

    TESTSTRING = 'test'
    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log']
    def test_task(args):
        return TESTSTRING

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1

    result_directory = os.path.join(results[0], 'output')
    assert all(f in expected_results for f in os.listdir(result_directory))

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        assert f.read() == json.dumps({'data': TESTSTRING})
    controller.stop()

def test_directory_output():
    controller = create_controller()
    controller.start()

    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log', 'testdir']
    TESTSTRING = b'\xDA'
    def test_task(args):
        import os
        os.mkdir('/golem/output/testdir')
        with open('/golem/output/testdir/testfile', 'wb') as f:
            f.write(TESTSTRING)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert all(f in expected_results for f in os.listdir(result_directory))
    files_in_testdir = os.listdir(os.path.join(result_directory, 'testdir'))
    assert len(files_in_testdir) == 1
    assert 'testfile' in files_in_testdir

    with open(os.path.join(result_directory, 'testdir', 'testfile'), 'rb') as f:
        assert f.read() == TESTSTRING
    controller.stop()

def test_directory_file_output():
    controller = create_controller()
    controller.start()

    expected_results = [GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log', 'testdir', 'testfile_top']
    TESTSTRING = b'\xDA'
    def test_task(args):
        import os
        os.mkdir('/golem/output/testdir')
        with open('/golem/output/testdir/testfile', 'wb') as f:
            f.write(TESTSTRING)
        with open('/golem/output/testfile_top', 'wb') as f:
            f.write(TESTSTRING)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert all(f in expected_results for f in os.listdir(result_directory))
    files_in_testdir = os.listdir(os.path.join(result_directory, 'testdir'))
    assert len(files_in_testdir) == 1
    assert 'testfile' in files_in_testdir

    with open(os.path.join(result_directory, 'testdir', 'testfile'), 'rb') as f:
        assert f.read() == TESTSTRING
    controller.stop()
