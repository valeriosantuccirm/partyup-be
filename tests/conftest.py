from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, Any]:
    yield TestClient(app=app)


# TODO: Add extensive tests once basic logic have been added
