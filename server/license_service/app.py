from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field


PLAN_SECONDS = {
    "day": 24 * 60 * 60,
    "week": 7 * 24 * 60 * 60,
    "month": 30 * 24 * 60 * 60,
}


def _decode_secret(value: str, name: str, minimum_bytes: int) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as error:
        raise RuntimeError(f"{name} 不是有效的 Base64URL") from error
    if len(decoded) < minimum_bytes:
        raise RuntimeError(f"{name} 至少需要 {minimum_bytes} 字节")
    return decoded


def _utc_text(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class Settings:
    database_path: Path
    auth_me_url: str
    hmac_secret: bytes
    signing_private_key: bytes
    admin_username: str = "3298003230"
    admin_user_id: int | None = None
    lease_seconds: int = 15 * 60
    auth_timeout_seconds: float = 5.0

    @classmethod
    def from_environment(cls) -> "Settings":
        hmac_value = os.environ.get("LICENSE_HMAC_SECRET_B64", "").strip()
        signing_value = os.environ.get("LICENSE_SIGNING_PRIVATE_KEY_B64", "").strip()
        if not hmac_value or not signing_value:
            raise RuntimeError("缺少 LICENSE_HMAC_SECRET_B64 或 LICENSE_SIGNING_PRIVATE_KEY_B64")

        admin_id_value = os.environ.get("LICENSE_ADMIN_USER_ID", "").strip()
        return cls(
            database_path=Path(os.environ.get("LICENSE_DATABASE_PATH", "./data/licenses.db")),
            auth_me_url=os.environ.get(
                "LICENSE_AUTH_ME_URL",
                "http://127.0.0.1:8088/api/auth/me",
            ).strip(),
            hmac_secret=_decode_secret(hmac_value, "LICENSE_HMAC_SECRET_B64", 32),
            signing_private_key=_decode_secret(
                signing_value,
                "LICENSE_SIGNING_PRIVATE_KEY_B64",
                32,
            )[:32],
            admin_username=os.environ.get("LICENSE_ADMIN_USERNAME", "3298003230").strip(),
            admin_user_id=int(admin_id_value) if admin_id_value else None,
            lease_seconds=max(60, min(3600, int(os.environ.get("LICENSE_LEASE_SECONDS", "900")))),
            auth_timeout_seconds=max(
                1.0,
                min(15.0, float(os.environ.get("LICENSE_AUTH_TIMEOUT_SECONDS", "5"))),
            ),
        )


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    role: str


class RedeemIn(BaseModel):
    code: str = Field(min_length=8, max_length=96)


class BatchCreateIn(BaseModel):
    plan: str
    quantity: int = Field(ge=1, le=100)
    note: str | None = Field(default=None, max_length=80)


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._entries: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float) -> bool:
        cutoff = now - self._window_seconds
        with self._lock:
            entries = self._entries[key]
            while entries and entries[0] <= cutoff:
                entries.popleft()
            if len(entries) >= self._limit:
                return False
            entries.append(now)
            if not entries:
                self._entries.pop(key, None)
            return True


class LicenseStore:
    def __init__(self, settings: Settings, now: Callable[[], int]) -> None:
        self._settings = settings
        self._now = now
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._settings.database_path,
            timeout=5.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS license_batches (
                    id TEXT PRIMARY KEY,
                    plan TEXT NOT NULL CHECK (plan IN ('day', 'week', 'month')),
                    duration_seconds INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    note TEXT,
                    created_by_id INTEGER NOT NULL,
                    created_by_username TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS license_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL REFERENCES license_batches(id),
                    code_hash BLOB NOT NULL UNIQUE,
                    code_hint TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unused'
                        CHECK (status IN ('unused', 'redeemed', 'revoked')),
                    redeemed_by_id INTEGER,
                    redeemed_at INTEGER,
                    revoked_at INTEGER
                );

                CREATE INDEX IF NOT EXISTS idx_license_codes_batch
                    ON license_codes(batch_id);
                CREATE INDEX IF NOT EXISTS idx_license_codes_redeemed_by
                    ON license_codes(redeemed_by_id);

                CREATE TABLE IF NOT EXISTS license_entitlements (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    activated_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS license_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    actor_user_id INTEGER NOT NULL,
                    actor_username TEXT NOT NULL,
                    target_user_id INTEGER,
                    batch_id TEXT,
                    code_hint TEXT,
                    created_at INTEGER NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_license_audit_created_at
                    ON license_audit(created_at DESC);
                """
            )

    def _hash_code(self, normalized_code: str) -> bytes:
        return hmac.new(
            self._settings.hmac_secret,
            normalized_code.encode("ascii"),
            hashlib.sha256,
        ).digest()

    @staticmethod
    def _normalize_code(code: str) -> str:
        normalized = "".join(character for character in code.upper() if character.isalnum())
        if len(normalized) < 24 or len(normalized) > 64:
            raise HTTPException(status_code=400, detail="卡密格式无效")
        return normalized

    @staticmethod
    def _new_code(plan: str) -> str:
        payload = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        parts = [payload[index : index + 4] for index in range(0, len(payload), 4)]
        return "-".join(("VC", plan[0].upper(), *parts))

    def status(self, principal: Principal) -> dict[str, object]:
        now = self._now()
        if self._is_admin(principal):
            return {
                "state": "unlimited",
                "is_unlimited": True,
                "activated_at": None,
                "expires_at": None,
                "server_time": _utc_text(now),
                "remaining_seconds": None,
            }

        with self._connect() as connection:
            row = connection.execute(
                "SELECT activated_at, expires_at FROM license_entitlements WHERE user_id = ?",
                (principal.user_id,),
            ).fetchone()
        if row is None:
            return {
                "state": "none",
                "is_unlimited": False,
                "activated_at": None,
                "expires_at": None,
                "server_time": _utc_text(now),
                "remaining_seconds": 0,
            }

        remaining = max(0, int(row["expires_at"]) - now)
        return {
            "state": "active" if remaining > 0 else "expired",
            "is_unlimited": False,
            "activated_at": _utc_text(int(row["activated_at"])),
            "expires_at": _utc_text(int(row["expires_at"])),
            "server_time": _utc_text(now),
            "remaining_seconds": remaining,
        }

    def create_batch(self, principal: Principal, plan: str, quantity: int, note: str | None) -> dict[str, object]:
        self.require_admin(principal)
        if plan not in PLAN_SECONDS:
            raise HTTPException(status_code=400, detail="卡密类型无效")

        now = self._now()
        batch_id = uuid.uuid4().hex
        codes: list[str] = []
        rows: list[tuple[str, bytes, str]] = []
        seen_hashes: set[bytes] = set()
        while len(codes) < quantity:
            code = self._new_code(plan)
            normalized = self._normalize_code(code)
            code_hash = self._hash_code(normalized)
            if code_hash in seen_hashes:
                continue
            seen_hashes.add(code_hash)
            codes.append(code)
            rows.append((batch_id, code_hash, f"{code[:7]}…{code[-4:]}"))

        clean_note = note.strip() if note and note.strip() else None
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO license_batches (
                        id, plan, duration_seconds, quantity, note,
                        created_by_id, created_by_username, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        plan,
                        PLAN_SECONDS[plan],
                        quantity,
                        clean_note,
                        principal.user_id,
                        principal.username,
                        now,
                    ),
                )
                connection.executemany(
                    "INSERT INTO license_codes (batch_id, code_hash, code_hint) VALUES (?, ?, ?)",
                    rows,
                )
                self._audit(
                    connection,
                    "batch_created",
                    principal,
                    now,
                    batch_id=batch_id,
                    details={"plan": plan, "quantity": quantity},
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        batch = self._batch_summary(batch_id)
        return {"batch": batch, "codes": codes}

    def list_batches(self, principal: Principal, limit: int) -> list[dict[str, object]]:
        self.require_admin(principal)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    b.id, b.plan, b.quantity, b.note, b.created_at,
                    b.created_by_username,
                    SUM(CASE WHEN c.status = 'unused' THEN 1 ELSE 0 END) AS unused_count,
                    SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) AS redeemed_count,
                    SUM(CASE WHEN c.status = 'revoked' THEN 1 ELSE 0 END) AS revoked_count
                FROM license_batches b
                JOIN license_codes c ON c.batch_id = b.id
                GROUP BY b.id
                ORDER BY b.created_at DESC, b.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._batch_row(row) for row in rows]

    def redeem(self, principal: Principal, code: str) -> tuple[str, dict[str, object]]:
        normalized = self._normalize_code(code)
        code_hash = self._hash_code(normalized)
        now = self._now()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                code_row = connection.execute(
                    """
                    SELECT c.id, c.batch_id, c.status, c.redeemed_by_id, c.code_hint,
                           b.duration_seconds
                    FROM license_codes c
                    JOIN license_batches b ON b.id = c.batch_id
                    WHERE c.code_hash = ?
                    """,
                    (code_hash,),
                ).fetchone()
                if code_row is None:
                    raise HTTPException(status_code=400, detail="卡密无效或已停用")
                if code_row["status"] == "revoked":
                    raise HTTPException(status_code=409, detail="卡密无效或已停用")
                if code_row["status"] == "redeemed":
                    if int(code_row["redeemed_by_id"] or 0) != principal.user_id:
                        raise HTTPException(status_code=409, detail="卡密已被使用")
                    connection.rollback()
                    return "该卡密已兑换，本次没有重复增加时长。", self.status(principal)

                entitlement = connection.execute(
                    "SELECT activated_at, expires_at FROM license_entitlements WHERE user_id = ?",
                    (principal.user_id,),
                ).fetchone()
                previous_expiry = int(entitlement["expires_at"]) if entitlement else 0
                activated_at = int(entitlement["activated_at"]) if entitlement else now
                expires_at = max(now, previous_expiry) + int(code_row["duration_seconds"])
                connection.execute(
                    """
                    INSERT INTO license_entitlements (
                        user_id, username, activated_at, expires_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        expires_at = excluded.expires_at,
                        updated_at = excluded.updated_at
                    """,
                    (principal.user_id, principal.username, activated_at, expires_at, now),
                )
                updated = connection.execute(
                    """
                    UPDATE license_codes
                    SET status = 'redeemed', redeemed_by_id = ?, redeemed_at = ?
                    WHERE id = ? AND status = 'unused'
                    """,
                    (principal.user_id, now, int(code_row["id"])),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("卡密状态在事务中发生变化")
                self._audit(
                    connection,
                    "code_redeemed",
                    principal,
                    now,
                    target_user_id=principal.user_id,
                    batch_id=str(code_row["batch_id"]),
                    code_hint=str(code_row["code_hint"]),
                    details={"expires_at": expires_at},
                )
                connection.commit()
            except HTTPException:
                connection.rollback()
                raise
            except Exception:
                connection.rollback()
                raise

        return "卡密已兑换，授权时长已更新。", self.status(principal)

    def require_active(self, principal: Principal) -> dict[str, object]:
        current = self.status(principal)
        if current["state"] not in {"active", "unlimited"}:
            raise HTTPException(status_code=403, detail="授权时长不足，无法启动推理")
        return current

    def require_admin(self, principal: Principal) -> None:
        if not self._is_admin(principal):
            raise HTTPException(status_code=403, detail="没有卡密管理权限")

    def _is_admin(self, principal: Principal) -> bool:
        if principal.username != self._settings.admin_username:
            return False
        return self._settings.admin_user_id is None or principal.user_id == self._settings.admin_user_id

    def _batch_summary(self, batch_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    b.id, b.plan, b.quantity, b.note, b.created_at,
                    b.created_by_username,
                    SUM(CASE WHEN c.status = 'unused' THEN 1 ELSE 0 END) AS unused_count,
                    SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) AS redeemed_count,
                    SUM(CASE WHEN c.status = 'revoked' THEN 1 ELSE 0 END) AS revoked_count
                FROM license_batches b
                JOIN license_codes c ON c.batch_id = b.id
                WHERE b.id = ?
                GROUP BY b.id
                """,
                (batch_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("新建卡密批次无法读取")
        return self._batch_row(row)

    @staticmethod
    def _batch_row(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": str(row["id"]),
            "plan": str(row["plan"]),
            "quantity": int(row["quantity"]),
            "unused_count": int(row["unused_count"] or 0),
            "redeemed_count": int(row["redeemed_count"] or 0),
            "revoked_count": int(row["revoked_count"] or 0),
            "note": row["note"],
            "created_at": _utc_text(int(row["created_at"])),
            "created_by": str(row["created_by_username"]),
        }

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        event: str,
        actor: Principal,
        created_at: int,
        *,
        target_user_id: int | None = None,
        batch_id: str | None = None,
        code_hint: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO license_audit (
                event, actor_user_id, actor_username, target_user_id,
                batch_id, code_hint, created_at, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event,
                actor.user_id,
                actor.username,
                target_user_id,
                batch_id,
                code_hint,
                created_at,
                json.dumps(details or {}, ensure_ascii=False, separators=(",", ":")),
            ),
        )


def _remote_auth_resolver(settings: Settings, token: str) -> Principal:
    request = urllib.request.Request(
        settings.auth_me_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.auth_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise HTTPException(status_code=401, detail="登录状态已失效") from error
        raise HTTPException(status_code=503, detail="账户服务暂时不可用") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="账户服务暂时不可用") from error

    try:
        return Principal(
            user_id=int(payload["id"]),
            username=str(payload["username"]),
            role=str(payload.get("role", "user")),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="账户服务返回了无效数据") from error


def create_app(
    settings: Settings | None = None,
    auth_resolver: Callable[[str], Principal] | None = None,
    now: Callable[[], int] | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_environment()
    clock = now or (lambda: int(time.time()))
    store = LicenseStore(active_settings, clock)
    signing_key = Ed25519PrivateKey.from_private_bytes(active_settings.signing_private_key)
    public_key = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    key_id = hashlib.sha256(public_key).hexdigest()[:16]
    resolve_auth = auth_resolver or (lambda token: _remote_auth_resolver(active_settings, token))
    limiter = SlidingWindowLimiter(limit=10, window_seconds=60)
    app = FastAPI(title="VisonCube License Service", version="1.0.0")

    def authenticated_user(authorization: str | None = Header(default=None)) -> Principal:
        scheme, separator, token = (authorization or "").partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="请先登录")
        return resolve_auth(token.strip())

    @app.get("/api/licenses/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "server_time": _utc_text(clock()), "key_id": key_id}

    @app.get("/api/licenses/public-key")
    def public_signing_key() -> dict[str, str]:
        return {"algorithm": "Ed25519", "key_id": key_id, "public_key": _base64url(public_key)}

    @app.get("/api/licenses/me")
    def my_license(principal: Principal = Depends(authenticated_user)) -> dict[str, object]:
        return store.status(principal)

    @app.post("/api/licenses/redeem")
    def redeem(
        body: RedeemIn,
        request: Request,
        principal: Principal = Depends(authenticated_user),
    ) -> dict[str, object]:
        client_host = request.client.host if request.client else "unknown"
        if not limiter.allow(f"{principal.user_id}:{client_host}", float(clock())):
            raise HTTPException(status_code=429, detail="兑换尝试过于频繁，请稍后再试")
        message, current = store.redeem(principal, body.code)
        return {"message": message, "license": current}

    @app.post("/api/licenses/lease")
    def issue_lease(principal: Principal = Depends(authenticated_user)) -> dict[str, object]:
        current = store.require_active(principal)
        issued_at = clock()
        entitlement_expiry = (
            issued_at + active_settings.lease_seconds
            if current["is_unlimited"]
            else int(datetime.fromisoformat(str(current["expires_at"]).replace("Z", "+00:00")).timestamp())
        )
        not_after = min(entitlement_expiry, issued_at + active_settings.lease_seconds)
        payload = {
            "version": 1,
            "sub": principal.user_id,
            "username": principal.username,
            "unlimited": bool(current["is_unlimited"]),
            "issued_at": issued_at,
            "not_after": not_after,
            "entitlement_expires_at": None if current["is_unlimited"] else entitlement_expiry,
            "nonce": _base64url(secrets.token_bytes(12)),
        }
        encoded_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = signing_key.sign(encoded_payload)
        return {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "payload": _base64url(encoded_payload),
            "signature": _base64url(signature),
        }

    @app.get("/api/licenses/admin/batches")
    def batches(
        limit: int = Query(default=50, ge=1, le=100),
        principal: Principal = Depends(authenticated_user),
    ) -> list[dict[str, object]]:
        return store.list_batches(principal, limit)

    @app.post("/api/licenses/admin/batches")
    def create_batch(
        body: BatchCreateIn,
        principal: Principal = Depends(authenticated_user),
    ) -> dict[str, object]:
        return store.create_batch(principal, body.plan, body.quantity, body.note)

    return app
