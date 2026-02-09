#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WebSocket 处理模块

提供实时日志推送和任务状态更新功能。
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

from .state import get_task_manager

router = APIRouter()
logger = logging.getLogger("WebSocket")


def clean_progress_bar_output(content: str) -> str:
    """
    清理日志输出中的回车符 (\\r)，保留 ANSI 颜色代码让 xterm.js 渲染
    
    进度条使用 \\r 回到行首覆盖显示，我们需要：
    1. 找到连续的 \\r 分隔的内容块（没有 \\n 分隔）
    2. 只保留每个块的最后一帧
    3. 确保输出有正确的换行
    """
    if '\r' not in content:
        return content
    
    result = []
    lines = content.split('\n')
    
    for line in lines:
        if '\r' not in line:
            result.append(line)
        else:
            # 这一行包含多个被 \r 分隔的"帧"
            parts = line.split('\r')
            
            # 处理策略：只保留最后一个非空的帧
            # \r 的语义是"回到行首"，所以最后一个帧是最终显示的内容
            last_non_empty = ''
            for part in reversed(parts):
                if part.strip():
                    last_non_empty = part
                    break
            
            if last_non_empty:
                result.append(last_non_empty)
    
    return '\n'.join(result)


class LogStreamer:
    """日志流管理器"""
    
    def __init__(self):
        # task_id -> set of websocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        
        if task_id not in self.connections:
            self.connections[task_id] = set()
        self.connections[task_id].add(websocket)
        
        logger.info(f"WebSocket 连接: task={task_id}")
    
    def disconnect(self, task_id: str, websocket: WebSocket):
        """断开连接"""
        if task_id in self.connections:
            self.connections[task_id].discard(websocket)
            if not self.connections[task_id]:
                del self.connections[task_id]
        
        logger.info(f"WebSocket 断开: task={task_id}")
    
    async def stream_log(self, task_id: str, websocket: WebSocket):
        """持续推送日志内容"""
        try:
            from .state import get_queue_manager
            
            queue_manager = get_queue_manager()
            
            if queue_manager is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "请先添加任务队列"
                })
                return
            
            # 在所有队列中查找任务
            task, manager = queue_manager.find_task_in_all_queues(task_id)
            
            if not task:
                await websocket.send_json({
                    "type": "error",
                    "message": "任务不存在"
                })
                return
            
            # 检查是否有日志文件
            if not task.log_file or not Path(task.log_file).exists():
                await websocket.send_json({
                    "type": "info",
                    "message": "等待日志文件生成..."
                })
                # 等待日志文件
                for _ in range(30):  # 最多等待 30 秒
                    await asyncio.sleep(1)
                    task, _ = queue_manager.find_task_in_all_queues(task_id)
                    if task and task.log_file and Path(task.log_file).exists():
                        break
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "日志文件未生成"
                    })
                    return
            
            log_path = Path(task.log_file)
            # 每个连接独立的读取位置和行缓冲区（不共享）
            last_pos = 0
            line_buffer = ''
            
            # 发送初始化信息（包含日志文件路径）
            await websocket.send_json({
                "type": "init",
                "log_file": str(task.log_file),
                "task_name": task.name
            })
            
            # 先发送历史日志（只发送最后 N 行以加快加载）
            MAX_HISTORY_LINES = 500
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                    content = f.read()
                    if content:
                        # 清理回车符但保留ANSI颜色
                        cleaned = clean_progress_bar_output(content)
                        # 只保留最后 N 行
                        lines = cleaned.split('\n')
                        if len(lines) > MAX_HISTORY_LINES:
                            cleaned = f"... (前 {len(lines) - MAX_HISTORY_LINES} 行已省略，可使用复制命令查看完整日志)\n" + '\n'.join(lines[-MAX_HISTORY_LINES:])
                        
                        await websocket.send_json({
                            "type": "log",
                            "content": cleaned
                        })
                    last_pos = f.tell()
            
            # 持续读取新内容
            while True:
                task, _ = queue_manager.find_task_in_all_queues(task_id)
                
                # 任务结束检查
                if not task or task.status.value not in ("running",):
                    # 读取剩余日志
                    if log_path.exists():
                        with open(log_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                            f.seek(last_pos)
                            remaining = f.read()
                            # 合并缓冲区中的内容
                            final_content = line_buffer + remaining
                            if final_content:
                                await websocket.send_json({
                                    "type": "log",
                                    "content": clean_progress_bar_output(final_content)
                                })
                    
                    await websocket.send_json({
                        "type": "end",
                        "status": task.status.value if task else "unknown",
                        "message": "任务已结束"
                    })
                    break
                
                # 读取新日志内容
                if log_path.exists():
                    with open(log_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                        f.seek(last_pos)
                        new_content = f.read()
                        if new_content:
                            # 合并上次未完成的行
                            full_content = line_buffer + new_content
                            
                            # 找到最后一个换行符，分离完整行和不完整行
                            last_newline = full_content.rfind('\n')
                            
                            if last_newline >= 0:
                                # 有完整行
                                complete_lines = full_content[:last_newline + 1]
                                line_buffer = full_content[last_newline + 1:]
                                
                                # 发送清理后的完整行
                                if complete_lines:
                                    await websocket.send_json({
                                        "type": "log",
                                        "content": clean_progress_bar_output(complete_lines)
                                    })
                            else:
                                # 没有完整行，全部缓冲
                                line_buffer = full_content
                            
                            last_pos = f.tell()
                
                await asyncio.sleep(0.5)  # 每 0.5 秒检查一次
                
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"日志流错误: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except:
                pass


# 全局日志流管理器
log_streamer = LogStreamer()


@router.websocket("/ws/logs/{task_id}")
async def websocket_logs(websocket: WebSocket, task_id: str):
    """任务日志 WebSocket 端点"""
    await log_streamer.connect(task_id, websocket)
    try:
        await log_streamer.stream_log(task_id, websocket)
    finally:
        log_streamer.disconnect(task_id, websocket)


@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """任务状态 WebSocket 端点（广播所有任务状态变化）"""
    await websocket.accept()
    
    try:
        last_state = {}
        
        while True:
            try:
                manager = get_task_manager()
                
                # 如果没有队列，返回空状态
                if manager is None:
                    current_state = {
                        "pending": [],
                        "running": [],
                        "history_count": 0,
                        "busy_gpus": []
                    }
                else:
                    # 获取当前状态
                    current_state = {
                        "pending": [t.to_dict() for t in manager.get_pending_tasks()],
                        "running": [t.to_dict() for t in manager.get_running_tasks()],
                        "history_count": manager.history_manager.count(),
                        "busy_gpus": list(manager.get_busy_gpus())
                    }
                
                # 只在状态变化时推送
                if current_state != last_state:
                    await websocket.send_json({
                        "type": "status_update",
                        "data": current_state
                    })
                    last_state = current_state.copy()
                
                await asyncio.sleep(1)  # 每秒检查一次
                
            except RuntimeError:
                # TaskManager 未初始化
                await asyncio.sleep(1)
                continue
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"状态 WebSocket 错误: {e}")
