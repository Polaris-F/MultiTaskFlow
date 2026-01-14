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


class LogStreamer:
    """日志流管理器"""
    
    def __init__(self):
        # task_id -> set of websocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}
        # task_id -> last read position
        self.file_positions: Dict[str, int] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        
        if task_id not in self.connections:
            self.connections[task_id] = set()
        self.connections[task_id].add(websocket)
        
        # 初始化文件位置
        if task_id not in self.file_positions:
            self.file_positions[task_id] = 0
        
        logger.info(f"WebSocket 连接: task={task_id}")
    
    def disconnect(self, task_id: str, websocket: WebSocket):
        """断开连接"""
        if task_id in self.connections:
            self.connections[task_id].discard(websocket)
            if not self.connections[task_id]:
                del self.connections[task_id]
                # 清理文件位置记录
                self.file_positions.pop(task_id, None)
        
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
            last_pos = self.file_positions.get(task_id, 0)
            
            # 先发送历史日志
            if log_path.exists() and last_pos == 0:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    if content:
                        await websocket.send_json({
                            "type": "log",
                            "content": content
                        })
                    last_pos = f.tell()
                    self.file_positions[task_id] = last_pos
            
            # 持续读取新内容
            while True:
                task, _ = queue_manager.find_task_in_all_queues(task_id)
                
                # 任务结束检查
                if not task or task.status.value not in ("running",):
                    # 读取剩余日志
                    if log_path.exists():
                        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                            f.seek(last_pos)
                            remaining = f.read()
                            if remaining:
                                await websocket.send_json({
                                    "type": "log",
                                    "content": remaining
                                })
                    
                    await websocket.send_json({
                        "type": "end",
                        "status": task.status.value if task else "unknown",
                        "message": "任务已结束"
                    })
                    break
                
                # 读取新日志内容
                if log_path.exists():
                    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        new_content = f.read()
                        if new_content:
                            await websocket.send_json({
                                "type": "log",
                                "content": new_content
                            })
                            last_pos = f.tell()
                            self.file_positions[task_id] = last_pos
                
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
                        "history_count": len(manager.history),
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
