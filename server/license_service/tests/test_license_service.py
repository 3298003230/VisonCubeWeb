from __future__ import annotations

import base64
import json
import sqlite3
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import (
    MAX_AUTH_RESPONSE_BYTES,
    Principal,
    Settings,
    SlidingWindowLimiter,
    _remote_auth_resolver,
    create_app,
)


class MutableClock:
    def __init__(self, value: int = 1_800_000_000) -> None:
        self.value = value

    def __call__(self) -> int:
        return self.value


def decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@pytest.fixture
def service(tmp_path: Path):
    signing_key = ec.generate_private_key(ec.SECP256R1())
    signing_bytes = signing_key.private_numbers().private_value.to_bytes(32, "big")
    settings = Settings(
        database_path=tmp_path / "licenses.db",
        auth_me_url="http://unused.test/api/auth/me",
        hmac_secret=b"h" * 32,
        signing_private_key=signing_bytes,
        admin_username="3298003230",
        admin_user_id=1,
        lease_seconds=900,
    )
    principals = {
        "admin": Principal(1, "3298003230", "admin"),
        "user-a": Principal(20, "user-a", "user"),
        "user-b": Principal(21, "user-b", "user"),
    }
    clock = MutableClock()
    app = create_app(settings, lambda token: principals[token], clock)
    with TestClient(app) as client:
        yield client, settings, signing_key.public_key(), clock


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_codes(client: TestClient, plan: str = "day", quantity: int = 1) -> list[str]:
    response = client.post(
        "/api/licenses/admin/batches",
        headers=auth("admin"),
        json={"plan": plan, "quantity": quantity, "note": "test"},
    )
    assert response.status_code == 200, response.text
    return response.json()["codes"]


def test_admin_is_unlimited_and_only_admin_can_generate(service) -> None:
    client, _, _, _ = service
    status_response = client.get("/api/licenses/me", headers=auth("admin"))
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "unlimited"
    assert status_response.json()["remaining_seconds"] is None

    forbidden = client.post(
        "/api/licenses/admin/batches",
        headers=auth("user-a"),
        json={"plan": "day", "quantity": 1},
    )
    assert forbidden.status_code == 403


def test_plaintext_codes_are_not_persisted_and_batch_counts_are_correct(service) -> None:
    client, settings, _, _ = service
    codes = create_codes(client, plan="week", quantity=3)
    assert len(codes) == 3
    assert len(set(codes)) == 3

    database_bytes = settings.database_path.read_bytes()
    for code in codes:
        assert code.encode("ascii") not in database_bytes

    batches = client.get("/api/licenses/admin/batches", headers=auth("admin"))
    assert batches.status_code == 200
    assert batches.json()[0]["quantity"] == 3
    assert batches.json()[0]["unused_count"] == 3


def test_redeem_is_idempotent_private_and_extends_from_existing_expiry(service) -> None:
    client, _, _, clock = service
    first, second = create_codes(client, quantity=2)

    redeemed = client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": first.lower()},
    )
    assert redeemed.status_code == 200
    initial_expiry = redeemed.json()["license"]["expires_at"]
    assert redeemed.json()["license"]["remaining_seconds"] == 86_400

    repeated = client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": first},
    )
    assert repeated.status_code == 200
    assert repeated.json()["license"]["expires_at"] == initial_expiry
    assert "没有重复" in repeated.json()["message"]

    stolen = client.post(
        "/api/licenses/redeem",
        headers=auth("user-b"),
        json={"code": first},
    )
    assert stolen.status_code == 409

    clock.value += 100
    extended = client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": second},
    )
    assert extended.status_code == 200
    assert extended.json()["license"]["remaining_seconds"] == 172_700


def test_expired_license_restarts_from_server_time(service) -> None:
    client, _, _, clock = service
    first = create_codes(client)[0]
    client.post("/api/licenses/redeem", headers=auth("user-a"), json={"code": first})
    clock.value += 90_000

    expired = client.get("/api/licenses/me", headers=auth("user-a"))
    assert expired.json()["state"] == "expired"
    assert expired.json()["remaining_seconds"] == 0

    second = create_codes(client)[0]
    renewed = client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": second},
    )
    assert renewed.status_code == 200
    assert renewed.json()["license"]["remaining_seconds"] == 86_400


def test_concurrent_redeem_adds_time_only_once(service) -> None:
    client, settings, _, clock = service
    code = create_codes(client)[0]

    def redeem_once():
        return client.post(
            "/api/licenses/redeem",
            headers=auth("user-a"),
            json={"code": code},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: redeem_once(), range(2)))

    assert [response.status_code for response in responses] == [200, 200]
    with sqlite3.connect(settings.database_path) as connection:
        entitlement = connection.execute(
            "SELECT expires_at FROM license_entitlements WHERE user_id = 20",
        ).fetchone()
        redeemed_count = connection.execute(
            "SELECT COUNT(*) FROM license_codes WHERE status = 'redeemed'",
        ).fetchone()[0]
    assert entitlement[0] == clock.value + 86_400
    assert redeemed_count == 1


def test_lease_requires_time_and_has_a_valid_signature(service) -> None:
    client, _, public_key, clock = service
    no_time = client.post("/api/licenses/lease", headers=auth("user-a"))
    assert no_time.status_code == 403

    code = create_codes(client, plan="month")[0]
    client.post("/api/licenses/redeem", headers=auth("user-a"), json={"code": code})
    lease = client.post("/api/licenses/lease", headers=auth("user-a"))
    assert lease.status_code == 200

    result = lease.json()
    payload_bytes = decode_base64url(result["payload"])
    signature = decode_base64url(result["signature"])
    signature_r = int.from_bytes(signature[:32], "big")
    signature_s = int.from_bytes(signature[32:], "big")
    public_key.verify(
        encode_dss_signature(signature_r, signature_s),
        payload_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
    payload = json.loads(payload_bytes)
    assert payload["sub"] == 20
    assert payload["issued_at"] == clock.value
    assert payload["not_after"] == clock.value + 900


def test_invalid_inputs_and_missing_auth_are_rejected(service) -> None:
    client, _, _, _ = service
    assert client.get("/api/licenses/me").status_code == 401
    assert client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": "not-a-real-code"},
    ).status_code == 400
    assert client.post(
        "/api/licenses/admin/batches",
        headers=auth("admin"),
        json={"plan": "year", "quantity": 1},
    ).status_code == 400

    with sqlite3.connect(service[1].database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(license_codes)")}
    assert "code" not in columns
    assert "plaintext" not in columns


def test_readiness_security_headers_and_strict_admin_identity(service, tmp_path: Path) -> None:
    client, settings, _, _ = service
    health = client.get("/api/licenses/health")
    assert health.status_code == 200
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["pragma"] == "no-cache"
    assert health.headers["x-content-type-options"] == "nosniff"

    ready = client.get("/api/licenses/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {
        "database": True,
        "admin_identity": True,
        "auth_endpoint": True,
    }

    unconfigured = Settings(
        database_path=tmp_path / "unconfigured.db",
        auth_me_url="not-a-valid-url",
        hmac_secret=b"u" * 32,
        signing_private_key=settings.signing_private_key,
        admin_username="3298003230",
        admin_user_id=None,
        lease_seconds=900,
    )
    app = create_app(unconfigured, lambda _: Principal(1, "3298003230", "admin"), MutableClock())
    with TestClient(app) as unconfigured_client:
        not_ready = unconfigured_client.get("/api/licenses/ready")
        assert not_ready.status_code == 503
        assert not_ready.json()["checks"]["admin_identity"] is False
        assert not_ready.json()["checks"]["auth_endpoint"] is False
        status_response = unconfigured_client.get("/api/licenses/me", headers=auth("admin"))
        assert status_response.json()["state"] == "none"
        forbidden = unconfigured_client.post(
            "/api/licenses/admin/batches",
            headers=auth("admin"),
            json={"plan": "day", "quantity": 1},
        )
        assert forbidden.status_code == 403


def test_admin_overview_code_pages_entitlements_and_audit(service) -> None:
    client, _, _, _ = service
    create_codes(client, plan="day", quantity=3)
    second_batch_codes = create_codes(client, plan="week", quantity=1)
    batches = client.get(
        "/api/licenses/admin/batches?limit=1&offset=1",
        headers=auth("admin"),
    )
    assert batches.status_code == 200
    assert len(batches.json()) == 1

    all_batches = client.get("/api/licenses/admin/batches", headers=auth("admin")).json()
    first_batch = next(batch for batch in all_batches if batch["quantity"] == 3)
    page = client.get(
        f"/api/licenses/admin/batches/{first_batch['id']}/codes?limit=2&offset=1",
        headers=auth("admin"),
    )
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2
    assert set(page.json()["items"][0]) == {
        "id",
        "batch_id",
        "code_hint",
        "status",
        "redeemed_by_id",
        "redeemed_at",
        "revoked_at",
    }
    assert "code_hash" not in page.text

    invalid_filter = client.get(
        f"/api/licenses/admin/batches/{first_batch['id']}/codes?status=unknown",
        headers=auth("admin"),
    )
    assert invalid_filter.status_code == 400
    missing_batch = client.get(
        "/api/licenses/admin/batches/missing/codes",
        headers=auth("admin"),
    )
    assert missing_batch.status_code == 404

    redeemed = client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": second_batch_codes[0]},
    )
    assert redeemed.status_code == 200
    entitlements = client.get(
        "/api/licenses/admin/entitlements?limit=10&offset=0",
        headers=auth("admin"),
    )
    assert entitlements.status_code == 200
    assert entitlements.json()["total"] == 1
    assert entitlements.json()["items"][0]["username"] == "user-a"
    assert entitlements.json()["items"][0]["state"] == "active"

    overview = client.get("/api/licenses/admin/overview", headers=auth("admin"))
    assert overview.status_code == 200
    assert overview.json()["batch_count"] == 2
    assert overview.json()["codes"] == {
        "total": 4,
        "unused": 3,
        "redeemed": 1,
        "revoked": 0,
    }
    assert overview.json()["entitlements"] == {"total": 1, "active": 1, "expired": 0}

    audit = client.get("/api/licenses/admin/audit?limit=2&offset=0", headers=auth("admin"))
    assert audit.status_code == 200
    assert audit.json()["total"] == 3
    assert len(audit.json()["items"]) == 2
    assert {item["event"] for item in audit.json()["items"]} <= {"batch_created", "code_redeemed"}


def test_revoke_code_is_admin_only_idempotent_and_never_removes_redeemed_time(service) -> None:
    client, _, _, _ = service
    codes = create_codes(client, quantity=2)
    batch = client.get("/api/licenses/admin/batches", headers=auth("admin")).json()[0]
    listed = client.get(
        f"/api/licenses/admin/batches/{batch['id']}/codes",
        headers=auth("admin"),
    ).json()["items"]

    forbidden = client.post(
        f"/api/licenses/admin/codes/{listed[0]['id']}/revoke",
        headers=auth("user-a"),
        json={"reason": "forbidden"},
    )
    assert forbidden.status_code == 403

    revoked = client.post(
        f"/api/licenses/admin/codes/{listed[0]['id']}/revoke",
        headers=auth("admin"),
        json={"reason": "测试停用"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["changed"] is True
    assert revoked.json()["code"]["status"] == "revoked"
    repeated = client.post(
        f"/api/licenses/admin/codes/{listed[0]['id']}/revoke",
        headers=auth("admin"),
    )
    assert repeated.status_code == 200
    assert repeated.json()["changed"] is False
    assert client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": codes[0]},
    ).status_code == 409

    redeemed = client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": codes[1]},
    )
    assert redeemed.status_code == 200
    expiry = redeemed.json()["license"]["expires_at"]
    cannot_revoke = client.post(
        f"/api/licenses/admin/codes/{listed[1]['id']}/revoke",
        headers=auth("admin"),
        json={},
    )
    assert cannot_revoke.status_code == 409
    current = client.get("/api/licenses/me", headers=auth("user-a"))
    assert current.json()["expires_at"] == expiry


def test_revoke_batch_only_changes_unused_codes_and_is_idempotent(service) -> None:
    client, _, _, _ = service
    codes = create_codes(client, quantity=3)
    batch = client.get("/api/licenses/admin/batches", headers=auth("admin")).json()[0]
    assert client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": codes[0]},
    ).status_code == 200

    revoked = client.post(
        f"/api/licenses/admin/batches/{batch['id']}/revoke",
        headers=auth("admin"),
        json={"reason": "批次撤回"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked_count"] == 2
    assert revoked.json()["batch"]["redeemed_count"] == 1
    assert revoked.json()["batch"]["revoked_count"] == 2
    repeated = client.post(
        f"/api/licenses/admin/batches/{batch['id']}/revoke",
        headers=auth("admin"),
    )
    assert repeated.status_code == 200
    assert repeated.json()["revoked_count"] == 0
    assert client.post(
        "/api/licenses/redeem",
        headers=auth("user-b"),
        json={"code": codes[1]},
    ).status_code == 409
    assert client.get("/api/licenses/me", headers=auth("user-a")).json()["state"] == "active"

    audit = client.get("/api/licenses/admin/audit", headers=auth("admin")).json()["items"]
    batch_revoked = next(item for item in audit if item["event"] == "batch_revoked")
    assert batch_revoked["details"] == {"revoked_count": 2, "reason": "批次撤回"}


def test_remote_auth_rejects_oversized_or_invalid_principals(service, monkeypatch) -> None:
    _, settings, _, _ = service

    class FakeResponse:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size: int) -> bytes:
            return self.body[:size]

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b"x" * (MAX_AUTH_RESPONSE_BYTES + 1)),
    )
    with pytest.raises(HTTPException) as oversized:
        _remote_auth_resolver(settings, "token")
    assert oversized.value.status_code == 503

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(json.dumps({"id": 0, "username": "user"}).encode()),
    )
    with pytest.raises(HTTPException) as invalid:
        _remote_auth_resolver(settings, "token")
    assert invalid.value.status_code == 503


def test_openapi_contains_complete_license_routes(service) -> None:
    client, _, _, _ = service
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        "/api/licenses/health",
        "/api/licenses/ready",
        "/api/licenses/public-key",
        "/api/licenses/me",
        "/api/licenses/redeem",
        "/api/licenses/lease",
        "/api/licenses/admin/overview",
        "/api/licenses/admin/batches",
        "/api/licenses/admin/batches/{batch_id}/codes",
        "/api/licenses/admin/codes/{code_id}/revoke",
        "/api/licenses/admin/batches/{batch_id}/revoke",
        "/api/licenses/admin/entitlements",
        "/api/licenses/admin/audit",
    } <= paths


def test_rate_limiter_reclaims_expired_keys() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10, max_keys=2)
    assert limiter.allow("first", 0.0) is True
    assert limiter.allow("second", 0.0) is True
    assert limiter.allow("third", 0.0) is False
    assert limiter.allow("third", 11.0) is True


def test_redeem_and_lease_rate_limits_return_retry_after(service) -> None:
    client, _, _, _ = service
    invalid_code = "VC-D-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA"
    for _ in range(10):
        response = client.post(
            "/api/licenses/redeem",
            headers=auth("user-b"),
            json={"code": invalid_code},
        )
        assert response.status_code == 400
    limited_redeem = client.post(
        "/api/licenses/redeem",
        headers=auth("user-b"),
        json={"code": invalid_code},
    )
    assert limited_redeem.status_code == 429
    assert limited_redeem.headers["retry-after"] == "60"

    code = create_codes(client)[0]
    assert client.post(
        "/api/licenses/redeem",
        headers=auth("user-a"),
        json={"code": code},
    ).status_code == 200
    for _ in range(30):
        assert client.post("/api/licenses/lease", headers=auth("user-a")).status_code == 200
    limited_lease = client.post("/api/licenses/lease", headers=auth("user-a"))
    assert limited_lease.status_code == 429
    assert limited_lease.headers["retry-after"] == "60"


def test_environment_rejects_invalid_signing_key_length_and_admin_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LICENSE_DATABASE_PATH", str(tmp_path / "environment.db"))
    monkeypatch.setenv("LICENSE_AUTH_ME_URL", "http://127.0.0.1:8088/api/auth/me")
    monkeypatch.setenv("LICENSE_HMAC_SECRET_B64", base64.urlsafe_b64encode(b"h" * 32).decode().rstrip("="))
    monkeypatch.setenv(
        "LICENSE_SIGNING_PRIVATE_KEY_B64",
        base64.urlsafe_b64encode(b"s" * 33).decode().rstrip("="),
    )
    monkeypatch.setenv("LICENSE_ADMIN_USER_ID", "1")
    with pytest.raises(RuntimeError, match="正好是 32 字节"):
        Settings.from_environment()

    monkeypatch.setenv(
        "LICENSE_SIGNING_PRIVATE_KEY_B64",
        base64.urlsafe_b64encode(b"s" * 32).decode().rstrip("="),
    )
    monkeypatch.setenv("LICENSE_ADMIN_USER_ID", "0")
    with pytest.raises(RuntimeError, match="必须是正整数"):
        Settings.from_environment()
