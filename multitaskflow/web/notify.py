#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知模块

提供任务完成/失败时的消息推送功能，支持 PushPlus 平台。
优先使用 Web UI 设置，其次使用环境变量。
"""

import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger("Notify")


def get_pushplus_token(workspace_dir: Path = None) -> Optional[str]:
    """
    获取 PushPlus Token
    
    优先级:
    1. 工作区设置文件 (.workspace.json 中的 pushplus_token)
    2. 环境变量 MSG_PUSH_TOKEN
    
    Args:
        workspace_dir: 工作区目录，包含 .workspace.json
        
    Returns:
        Token 字符串，如果未配置则返回 None
    """
    # 1. 尝试从工作区设置读取
    if workspace_dir:
        workspace_file = workspace_dir / ".workspace.json"
        if workspace_file.exists():
            try:
                import json
                data = json.loads(workspace_file.read_text())
                token = data.get("pushplus_token", "").strip()
                if token:
                    return token
            except Exception:
                pass
    
    # 2. 尝试从环境变量读取
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    token = os.getenv("MSG_PUSH_TOKEN", "").strip()
    return token if token else None


def get_last_n_lines(file_path: str, n: int = 10) -> str:
    """
    获取文件最后 N 行
    
    Args:
        file_path: 日志文件路径
        n: 行数，默认 10
        
    Returns:
        最后 N 行内容
    """
    if not file_path or not Path(file_path).exists():
        return "(日志不可用)"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            last_lines = lines[-n:] if len(lines) >= n else lines
            return ''.join(last_lines).strip()
    except Exception as e:
        return f"(读取日志失败: {e})"


def send_pushplus(token: str, title: str, content: str) -> bool:
    """
    发送消息到 PushPlus 平台
    
    Args:
        token: PushPlus Token
        title: 消息标题
        content: 消息内容（支持 HTML）
        
    Returns:
        是否发送成功
    """
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": "html"  # 使用 HTML 模板
    }
    
    max_retries = 3
    base_wait_time = 2
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = base_wait_time * (2 ** attempt)
                logger.info(f"重试发送消息 ({attempt + 1}/{max_retries})，等待 {wait_time}s...")
                time.sleep(wait_time)
            
            response = requests.post(
                'https://www.pushplus.plus/send',
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            result = response.json()
            if response.status_code == 200 and result.get('code') == 200:
                logger.info("消息推送成功")
                return True
            elif result.get('code') == 429:
                logger.warning("消息发送受到频率限制，重试中...")
                continue
            else:
                logger.warning(f"消息发送失败: {result}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"消息发送请求失败: {e}")
    
    logger.error("消息推送失败，已达最大重试次数")
    return False


def send_task_notification(
    task_name: str,
    status: str,
    log_file: str = None,
    duration: float = None,
    error_message: str = None,
    workspace_dir: Path = None
) -> bool:
    """
    发送任务完成/失败通知
    
    Args:
        task_name: 任务名称
        status: 任务状态 (completed/failed/stopped)
        log_file: 日志文件路径
        duration: 运行时长（秒）
        error_message: 错误信息
        workspace_dir: 工作区目录
        
    Returns:
        是否发送成功
    """
    token = get_pushplus_token(workspace_dir)
    if not token:
        logger.debug("未配置 PushPlus Token，跳过通知")
        return False
    
    # 状态图标和颜色
    status_config = {
        "completed": ("✅", "任务完成", "#22c55e"),
        "failed": ("❌", "任务失败", "#ef4444"),
        "stopped": ("⏹️", "任务停止", "#f59e0b"),
    }
    
    icon, status_text, color = status_config.get(status, ("❓", "状态未知", "#6b7280"))
    
    # 格式化时长
    duration_str = ""
    if duration:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        if hours > 0:
            duration_str = f"{hours}小时{minutes}分钟"
        else:
            duration_str = f"{minutes}分钟"
    
    # 获取日志尾部
    log_tail = get_last_n_lines(log_file, 10)
    
    # 生成 HTML 内容
    title = f"{icon} {task_name} - {status_text}"
    
    content = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 16px; max-width: 600px;">
    <div style="background: {color}20; border-left: 4px solid {color}; padding: 12px; margin-bottom: 16px; border-radius: 4px;">
        <h2 style="margin: 0; color: {color};">{icon} {status_text}</h2>
        <p style="margin: 8px 0 0 0; color: #374151;"><strong>{task_name}</strong></p>
    </div>
    
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
        <tr>
            <td style="padding: 8px 0; color: #6b7280;">⏱ 运行时长</td>
            <td style="padding: 8px 0; color: #1f2937;">{duration_str or '未知'}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; color: #6b7280;">🕐 完成时间</td>
            <td style="padding: 8px 0; color: #1f2937;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
    </table>
    
    {"<div style='background: #fef2f2; border: 1px solid #fecaca; padding: 12px; border-radius: 4px; margin-bottom: 16px;'><strong>❌ 错误信息:</strong><br>" + error_message + "</div>" if error_message else ""}
    
    <div style="margin-top: 16px;">
        <h3 style="margin: 0 0 8px 0; color: #374151;">📄 日志尾部 (最后10行)</h3>
        <pre style="background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; line-height: 1.5;">{log_tail}</pre>
    </div>
    
    <p style="color: #9ca3af; font-size: 12px; margin-top: 16px;">
        —— 由 MultiTaskFlow WebUI 发送
    </p>
</div>
"""
    
    return send_pushplus(token, title, content)


def save_pushplus_token(workspace_dir: Path, token: str) -> bool:
    """
    保存 PushPlus Token 到工作区
    
    Args:
        workspace_dir: 工作区目录
        token: Token 字符串
        
    Returns:
        是否保存成功
    """
    import json
    
    workspace_file = workspace_dir / ".workspace.json"
    
    try:
        # 读取现有数据
        data = {}
        if workspace_file.exists():
            data = json.loads(workspace_file.read_text())
        
        # 更新 token
        data["pushplus_token"] = token.strip()
        
        # 保存
        workspace_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("PushPlus Token 已保存到工作区")
        return True
    except Exception as e:
        logger.error(f"保存 Token 失败: {e}")
        return False
