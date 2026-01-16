#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证模块

提供简单的密码认证功能。
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel


router = APIRouter()

# 会话存储（内存中）
_sessions: dict[str, datetime] = {}

# 会话过期时间（小时）
SESSION_EXPIRE_HOURS = 24

# 密码文件路径
def _get_password_file() -> Path:
    """获取密码文件路径"""
    return Path.home() / ".multitaskflow" / "auth.txt"


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
    token = secrets.token_urlsafe(32)
    _sessions[token] = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
    return token


def verify_session(token: str) -> bool:
    """验证会话"""
    if token not in _sessions:
        return False
    if datetime.now() > _sessions[token]:
        del _sessions[token]
        return False
    return True


def clear_session(token: str):
    """清除会话"""
    if token in _sessions:
        del _sessions[token]


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
