from typing import Any, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database.models.psql.user import User
from app.main import app
from tests.mocks import CURRENT_AUTH_USER


@pytest.fixture
def client() -> Generator[TestClient, Any, None]:
    yield TestClient(app=app)


@pytest.fixture
def mock_auth_user() -> Generator[User, Any, None]:
    yield User(**CURRENT_AUTH_USER, guid=uuid4())
