import asyncio
from copy import deepcopy

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import activities, app


@pytest.fixture
def reset_activities_state():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


async def _request(method: str, url: str, **kwargs):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, url, **kwargs)


def test_root_redirects_to_static_index(reset_activities_state):
    # Arrange
    request_method = "GET"
    request_url = "/"

    # Act
    response = asyncio.run(_request(request_method, request_url, follow_redirects=False))

    # Assert
    assert response.status_code in (307, 308)
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_expected_structure(reset_activities_state):
    # Arrange
    request_method = "GET"
    request_url = "/activities"

    # Act
    response = asyncio.run(_request(request_method, request_url))
    payload = response.json()

    # Assert
    assert response.status_code == 200
    assert isinstance(payload, dict)
    assert "Chess Club" in payload
    assert "participants" in payload["Chess Club"]
    assert isinstance(payload["Chess Club"]["participants"], list)


def test_signup_successfully_adds_new_participant(reset_activities_state):
    # Arrange
    activity_name = "Chess Club"
    new_email = "newstudent@mergington.edu"
    request_method = "POST"
    request_url = f"/activities/{activity_name}/signup"

    # Act
    response = asyncio.run(_request(request_method, request_url, params={"email": new_email}))
    payload = response.json()

    # Assert
    assert response.status_code == 200
    assert payload["message"] == f"Signed up {new_email} for {activity_name}"
    assert new_email in activities[activity_name]["participants"]


def test_signup_returns_404_for_unknown_activity(reset_activities_state):
    # Arrange
    unknown_activity = "Unknown Activity"
    email = "student@mergington.edu"
    request_method = "POST"
    request_url = f"/activities/{unknown_activity}/signup"

    # Act
    response = asyncio.run(_request(request_method, request_url, params={"email": email}))
    payload = response.json()

    # Assert
    assert response.status_code == 404
    assert payload["detail"] == "Activity not found"


def test_signup_returns_400_for_duplicate_participant(reset_activities_state):
    # Arrange
    activity_name = "Chess Club"
    existing_email = activities[activity_name]["participants"][0]
    request_method = "POST"
    request_url = f"/activities/{activity_name}/signup"

    # Act
    response = asyncio.run(_request(request_method, request_url, params={"email": existing_email}))
    payload = response.json()

    # Assert
    assert response.status_code == 400
    assert payload["detail"] == "Student already signed up for this activity"
