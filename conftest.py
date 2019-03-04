import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--remote", action="store_true", default=False, help="Test with remote file upload")

@pytest.fixture
def remote(request):
    return request.config.getoption("--remote")
