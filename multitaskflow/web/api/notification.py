#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知设置 API
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ..state import get_queue_manager
from .auth import require_auth

router = APIRouter()


class NotificationSettings(BaseModel):
    pushplus_token: Optional[str] = None
    enabled: bool = True


class NotificationSettingsResponse(BaseModel):
    pushplus_token: str = ""
    enabled: bool = True
    has_env_token: bool = False


@router.get("/settings/notification")
async def get_notification_settings(_=Depends(require_auth)) -> NotificationSettingsResponse:
    """获取通知设置"""
    import os
    import json
    
    queue_manager = get_queue_manager()
    
    # 检查环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    has_env_token = bool(os.getenv("MSG_PUSH_TOKEN", "").strip())
    
    # 检查工作区设置
    token = ""
    enabled = True
    
    if queue_manager:
        workspace_file = queue_manager.workspace_dir / ".workspace.json"
        if workspace_file.exists():
            try:
                data = json.loads(workspace_file.read_text())
                token = data.get("pushplus_token", "")
                enabled = data.get("notification_enabled", True)
            except Exception:
                pass
    
    return NotificationSettingsResponse(
        pushplus_token=token,
        enabled=enabled,
        has_env_token=has_env_token
    )


@router.post("/settings/notification")
async def save_notification_settings(settings: NotificationSettings, _=Depends(require_auth)):
    """保存通知设置"""
    import json
    
    queue_manager = get_queue_manager()
    if not queue_manager:
        return {"success": False, "message": "无工作区"}
    
    workspace_file = queue_manager.workspace_dir / ".workspace.json"
    
    try:
        # 读取现有数据
        data = {}
        if workspace_file.exists():
            data = json.loads(workspace_file.read_text())
        
        # 更新设置
        if settings.pushplus_token is not None:
            data["pushplus_token"] = settings.pushplus_token.strip()
        data["notification_enabled"] = settings.enabled
        
        # 保存
        workspace_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        
        return {"success": True, "message": "设置已保存"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/settings/notification/test")
async def test_notification(_=Depends(require_auth)):
    """发送测试通知"""
    from ..notify import send_task_notification
    
    queue_manager = get_queue_manager()
    workspace_dir = queue_manager.workspace_dir if queue_manager else None
    
    success = send_task_notification(
        task_name="测试任务",
        status="completed",
        log_file=None,
        duration=3600,  # 1小时
        error_message=None,
        workspace_dir=workspace_dir
    )
    
    if success:
        return {"success": True, "message": "测试通知已发送"}
    else:
        return {"success": False, "message": "发送失败，请检查 Token 配置"}
