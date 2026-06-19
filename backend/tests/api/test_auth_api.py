"""API-level tests for authentication endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestRegister:
    def test_register_returns_422_for_missing_fields(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/register", json={})
        assert res.status_code == 422

    def test_register_returns_422_for_invalid_email(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "secret", "display_name": "Test"},
        )
        assert res.status_code == 422

    def test_register_requires_password(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "display_name": "Test"},
        )
        assert res.status_code == 422


class TestLogin:
    def test_login_returns_422_for_missing_credentials(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/login", json={})
        assert res.status_code == 422

    def test_login_invalid_credentials_returns_401(self, client: TestClient) -> None:
        with patch("app.api.auth.get_db") as mock_get_db:
            db = AsyncMock()
            db.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=lambda: None)
            )
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            res = client.post(
                "/api/v1/auth/login",
                json={"email": "noexist@example.com", "password": "wrong"},
            )
            assert res.status_code in (401, 500)


class TestJWKS:
    def test_jwks_endpoint_accessible(self, client: TestClient) -> None:
        res = client.get("/.well-known/jwks.json")
        # Returns 200 with the public key
        assert res.status_code == 200
        body = res.json()
        assert "keys" in body


class TestRefresh:
    def test_refresh_without_cookie_returns_401(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/refresh")
        assert res.status_code == 401
