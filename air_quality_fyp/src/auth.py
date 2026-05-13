from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple

import streamlit as st


@dataclass(frozen=True)
class AuthUser:
    email: str


def _get_secret(key: str) -> Optional[str]:
    try:
        val = st.secrets.get(key)
    except Exception:
        val = None
    if val is None:
        val = os.environ.get(key)
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _db_connect():
    """
    MySQL connection from .streamlit/secrets.toml or env:
    DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT (default 3306)
    """
    try:
        import pymysql  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "缺少依赖 pymysql。请先安装：pip install pymysql"
        ) from e

    host = _get_secret("DB_HOST")
    name = _get_secret("DB_NAME")
    user = _get_secret("DB_USER")
    password = _get_secret("DB_PASS")
    port_str = _get_secret("DB_PORT") or "3306"
    port = int(port_str)

    missing = [k for k, v in [("DB_HOST", host), ("DB_NAME", name), ("DB_USER", user), ("DB_PASS", password)] if not v]
    if missing:
        raise RuntimeError(
            "未配置 MySQL 连接信息。请在 `.streamlit/secrets.toml` 设置："
            + ", ".join(missing)
        )

    # Create database if it does not exist (connect without database first)
    conn_no_db = pymysql.connect(
        host=host or "localhost",
        user=user,
        password=password,
        port=port,
        charset="utf8mb4",
    )
    try:
        with conn_no_db.cursor() as cur:
            safe_name = name.replace("`", "``")
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{safe_name}`")
        conn_no_db.commit()
    finally:
        conn_no_db.close()

    return pymysql.connect(
        host=host or "localhost",
        user=user,
        password=password,
        database=name,
        port=port,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_auth_db() -> None:
    conn = _db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  email VARCHAR(255) UNIQUE NOT NULL,
                  pass_hash TEXT NOT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        conn.commit()
    finally:
        conn.close()


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _pbkdf2_hash(password: str, salt: bytes, iterations: int = 210_000) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def _encode_hash(salt: bytes, iterations: int, dk: bytes) -> str:
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def _decode_hash(encoded: str) -> Tuple[int, bytes, bytes]:
    algo, it_s, salt_hex, dk_hex = (encoded or "").split("$", 3)
    if algo != "pbkdf2_sha256":
        raise ValueError("Unsupported password hash format")
    return int(it_s), bytes.fromhex(salt_hex), bytes.fromhex(dk_hex)


def create_user(email: str, password: str) -> Tuple[bool, str]:
    try:
        init_auth_db()
    except Exception as e:
        return False, str(e)
    email_n = _normalize_email(email)
    if not email_n or "@" not in email_n:
        return False, "请输入有效邮箱。"
    if not password or len(password) < 8:
        return False, "密码至少 8 位。"

    salt = secrets.token_bytes(16)
    iterations = 210_000
    dk = _pbkdf2_hash(password, salt, iterations)
    encoded = _encode_hash(salt, iterations, dk)

    try:
        conn = _db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users(email, pass_hash) VALUES (%s, %s)",
                    (email_n, encoded),
                )
            conn.commit()
            return True, "注册成功，请登录。"
        finally:
            conn.close()
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower() or "unique" in msg.lower() or "1062" in msg:
            return False, "该邮箱已注册，请直接登录。"
        return False, msg


def authenticate(email: str, password: str) -> Tuple[bool, str]:
    try:
        init_auth_db()
    except Exception as e:
        return False, str(e)
    email_n = _normalize_email(email)
    if not email_n or not password:
        return False, "请输入邮箱和密码。"

    conn = _db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pass_hash FROM users WHERE email = %s", (email_n,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return False, "账号不存在。"

    encoded = row["pass_hash"]
    try:
        iterations, salt, expected = _decode_hash(encoded)
        got = _pbkdf2_hash(password, salt, iterations)
        if hmac.compare_digest(got, expected):
            return True, "登录成功。"
        return False, "密码错误。"
    except Exception:
        return False, "账号数据异常，请联系管理员。"


def logout() -> None:
    st.session_state.pop("auth_user", None)
    st.session_state.pop("auth_email", None)


def current_user() -> Optional[AuthUser]:
    email = st.session_state.get("auth_email")
    if email:
        return AuthUser(email=str(email))
    return None


def login_as(email: str) -> None:
    st.session_state["auth_email"] = _normalize_email(email)
    st.session_state["auth_user"] = True


def _db_configured() -> bool:
    """Return True only if all required DB secrets are present."""
    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASS"]
    return all(_get_secret(k) for k in required)


def require_login() -> None:
    """
    Call this near the top of every page (after st.set_page_config).
    Stops the page unless user is logged in.
    If no DB is configured (e.g. Streamlit Cloud demo), auto-login as guest.
    """
    # Demo mode: no DB configured → auto-login as guest so app is viewable
    if not _db_configured():
        st.session_state["auth_user"] = True
        st.session_state["auth_email"] = "demo@guest"
        return

    if st.session_state.get("auth_user") and st.session_state.get("auth_email"):
        return

    st.warning("🔒 请先登录后再访问此页面。")
    st.markdown('[🔑 ➡️ 去登录页面](/Login)')
    st.stop()


def render_auth_status_in_sidebar() -> None:
    """
    Optional: show auth status in sidebar.
    Safe to call on any page.
    """
    user = current_user()
    with st.sidebar:
        st.markdown("---")
        if user:
            st.caption("已登录")
            st.code(user.email, language=None)
            if st.button("退出登录"):
                logout()
                st.experimental_rerun()
        else:
            st.caption("未登录")
            st.markdown('[🔑 去登录](/Login)')

