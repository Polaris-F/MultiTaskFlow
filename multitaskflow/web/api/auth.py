#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证模块

提供简单的密码认证功能，支持会话持久化。
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel


router = APIRouter()

# 会话过期时间（小时）
SESSION_EXPIRE_HOURS = 24 * 7  # 7 天

# 配置目录
def _get_config_dir() -> Path:
    """获取配置目录"""
    config_dir = Path.home() / ".multitaskflow"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_password_file() -> Path:
    """获取密码文件路径"""
    return _get_config_dir() / "auth.txt"


def _get_sessions_file() -> Path:
    """获取会话文件路径"""
    return _get_config_dir() / "sessions.json"


# 会话存储（内存缓存 + 文件持久化）
_sessions: dict[str, datetime] = {}
_sessions_loaded = False


def _load_sessions():
    """从文件加载会话"""
    global _sessions, _sessions_loaded
    if _sessions_loaded:
        return
    
    sessions_file = _get_sessions_file()
    if sessions_file.exists():
        try:
            data = json.loads(sessions_file.read_text())
            now = datetime.now()
            for token, expire_str in data.items():
                expire = datetime.fromisoformat(expire_str)
                if expire > now:
                    _sessions[token] = expire
        except Exception:
            pass  # 忽略加载错误
    _sessions_loaded = True


def _save_sessions():
    """保存会话到文件"""
    sessions_file = _get_sessions_file()
    data = {token: expire.isoformat() for token, expire in _sessions.items()}
    try:
        sessions_file.write_text(json.dumps(data, indent=2))
    except Exception:
        pass  # 忽略保存错误


def _hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def _get_stored_password() -> Optional[str]:
    """获取存储的密码哈希"""
    pw_file = _get_password_file()
    if pw_file.exists():
        return pw_file.read_text().strip()
    return None


def _set_password(password: str):
    """设置密码"""
    pw_file = _get_password_file()
    pw_file.parent.mkdir(parents=True, exist_ok=True)
    pw_file.write_text(_hash_password(password))


def is_auth_enabled() -> bool:
    """检查是否已启用认证"""
    return _get_stored_password() is not None


def verify_password(password: str) -> bool:
    """验证密码"""
    stored = _get_stored_password()
    if not stored:
        return False
    return _hash_password(password) == stored


def create_session() -> str:
    """创建新会话"""
    _load_sessions()
    token = secrets.token_urlsafe(32)
    _sessions[token] = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
    _save_sessions()
    return token


def verify_session(token: str) -> bool:
    """验证会话"""
    _load_sessions()
    if token not in _sessions:
        return False
    if datetime.now() > _sessions[token]:
        del _sessions[token]
        _save_sessions()
        return False
    return True


def clear_session(token: str):
    """清除会话"""
    _load_sessions()
    if token in _sessions:
        del _sessions[token]
        _save_sessions()


# API 模型
class LoginRequest(BaseModel):
    password: str


class SetPasswordRequest(BaseModel):
    password: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    auth_enabled: bool


# API 路由
@router.get("/auth/status")
async def auth_status(request: Request) -> AuthStatusResponse:
    """获取认证状态"""
    token = request.cookies.get("session_token")
    authenticated = verify_session(token) if token else False
    return AuthStatusResponse(
        authenticated=authenticated,
        auth_enabled=is_auth_enabled()
    )


@router.post("/auth/login")
async def login(request: LoginRequest, response: Response):
    """登录"""
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="认证未启用")
    
    if not verify_password(request.password):
        raise HTTPException(status_code=401, detail="密码错误")
    
    token = create_session()
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=SESSION_EXPIRE_HOURS * 3600,
        samesite="strict"
    )
    return {"success": True, "message": "登录成功"}


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """登出"""
    token = request.cookies.get("session_token")
    if token:
        clear_session(token)
    response.delete_cookie("session_token")
    return {"success": True, "message": "已登出"}


@router.post("/auth/setup")
async def setup_password(request: SetPasswordRequest, req: Request, response: Response):
    """设置密码（仅首次）"""
    if is_auth_enabled():
        # 已设置密码，需要验证当前会话
        token = req.cookies.get("session_token")
        if not verify_session(token) if token else True:
            raise HTTPException(status_code=401, detail="需要先登录")
    
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4位")
    
    _set_password(request.password)
    
    # 自动登录
    token = create_session()
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=SESSION_EXPIRE_HOURS * 3600,
        samesite="strict"
    )
    return {"success": True, "message": "密码已设置"}


# 认证依赖
async def require_auth(request: Request):
    """认证依赖 - 用于保护 API"""
    if not is_auth_enabled():
        return  # 未启用认证，直接通过
    
    token = request.cookies.get("session_token")
    if not token or not verify_session(token):
        raise HTTPException(status_code=401, detail="未认证")
