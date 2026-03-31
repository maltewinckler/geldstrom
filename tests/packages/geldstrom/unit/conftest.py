"""Unit test configuration and fixtures.

This conftest provides common fixtures and configuration for unit tests.
"""

import glob
import os.path
from unittest import mock

import pytest

# Test messages directory for parser/serializer tests
TEST_MESSAGES = {
    os.path.basename(f).rsplit(".")[0]: open(f, "rb").read()
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "messages", "*.bin"))
}


@pytest.fixture
def mocker(request):
    """Provide a simple mocker utility for patching."""

    class _Mocker:
        def patch(self, target, *args, **kwargs):
            patcher = mock.patch(target, *args, **kwargs)
            mocked = patcher.start()
            request.addfinalizer(patcher.stop)
            return mocked

        def __getattr__(self, name):
            return getattr(mock, name)

    return _Mocker()
