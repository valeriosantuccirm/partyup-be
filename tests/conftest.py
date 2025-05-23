from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, Any, None]:
    yield TestClient(app=app)


# TODO: Add extensive tests once basic logic have been added
