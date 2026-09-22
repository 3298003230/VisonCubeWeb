from __future__ import annotations

import base64
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from fastapi.testclient import TestClient

from app import Principal, Settings, create_app


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
