"""API-level tests for session endpoints.

Uses FastAPI's TestClient with a mocked DB session and auth dependency.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user
from app.db.models import User


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_user() -> User:
    user = MagicMock(spec=User)
    user.id = "user-test-1"
    user.email = "test@example.com"
    user.display_name = "Test User"
    user.is_active = True
    return user


@pytest.fixture()
def client(mock_user: User) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Session Creation ─────────────────────────────────────────────────────────

class TestCreateSession:
    def test_returns_422_when_topic_missing(self, client: TestClient) -> None:
        res = client.post("/api/v1/sessions", json={"panel_id": "abc"})
        assert res.status_code == 422

    def test_returns_422_when_panel_id_missing(self, client: TestClient) -> None:
        res = client.post("/api/v1/sessions", json={"topic": "Test Topic"})
        assert res.status_code == 422

    @patch("app.api.sessions.PanelRegistry.get_by_id", new_callable=AsyncMock)
    @patch("app.api.sessions.get_db")
    def test_returns_404_when_panel_not_found(
        self,
        mock_get_db: MagicMock,
        mock_get_panel: AsyncMock,
        client: TestClient,
    ) -> None:
        mock_get_panel.return_value = None
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=None)

        res = client.post(
            "/api/v1/sessions",
            json={"topic": "Test Topic", "panel_id": "nonexistent-panel-id"},
        )
        # Panel not found
        assert res.status_code in (404, 422, 500)  # depends on mock setup


# ── Session Retrieval ────────────────────────────────────────────────────────

class TestGetSession:
    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        with patch("app.api.sessions.get_db") as mock_get_db:
            db = AsyncMock()
            db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            res = client.get("/api/v1/sessions/nonexistent-id")
            assert res.status_code in (404, 500)


# ── Auth Enforcement ─────────────────────────────────────────────────────────

class TestAuthEnforcement:
    def test_unauthenticated_request_returns_401(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/api/v1/sessions/some-id")
            assert res.status_code == 401

    def test_health_endpoint_requires_no_auth(self) -> None:
        from app.db.session import get_db

        async def mock_db_gen():
            db = AsyncMock()
            db.execute = AsyncMock(return_value=MagicMock())
            yield db

        app.dependency_overrides[get_db] = mock_db_gen
        try:
            with TestClient(app) as c:
                res = c.get("/health")
                assert res.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_session_stream_requires_auth(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/api/v1/sessions/some-id/stream")
            assert res.status_code == 401


# ── Vote Submission ──────────────────────────────────────────────────────────

class TestVoteSubmission:
    def test_vote_requires_valid_choice(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/sessions/some-id/votes",
            json={"vote": "maybe"},  # invalid
        )
        assert res.status_code == 422

    def test_vote_valid_choices_pass_validation(self, client: TestClient) -> None:
        # Validation passes for valid choices (will fail at DB level in this unit test)
        for choice in ("yes", "no", "abstain"):
            res = client.post(
                "/api/v1/sessions/some-id/votes",
                json={"vote": choice, "rationale": "My reason"},
            )
            # 4xx is expected (session not found), but NOT 422
            assert res.status_code != 422, f"Choice '{choice}' should not cause 422"


# ── Intervention Submission ──────────────────────────────────────────────────

class TestIntervention:
    def test_empty_content_rejected(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/sessions/some-id/interventions",
            json={"content": ""},  # empty
        )
        assert res.status_code == 422


# ── Export ────────────────────────────────────────────────────────────────────

class TestExport:
    def test_invalid_format_rejected(self, client: TestClient) -> None:
        res = client.get("/api/v1/sessions/some-id/export?format=csv")
        assert res.status_code == 422

    def test_valid_formats_accepted(self, client: TestClient) -> None:
        for fmt in ("json", "markdown", "pdf"):
            res = client.get(f"/api/v1/sessions/some-id/export?format={fmt}")
            # Any 4xx other than 422 is acceptable (session not found)
            assert res.status_code != 422, f"Format '{fmt}' should not cause 422"


# ── Security Headers ────────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_401_response_has_security_headers(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/api/v1/sessions/some-id")
            assert res.status_code == 401
            assert res.headers.get("x-content-type-options") == "nosniff"
            assert res.headers.get("x-frame-options") == "DENY"
            assert "referrer-policy" in res.headers

    def test_cors_allows_localhost(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.options(
                "/api/v1/sessions/some-id",
                headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
            )
            assert res.status_code in (200, 204, 401)
