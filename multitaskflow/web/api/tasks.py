#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务 CRUD API

提供任务的增删改查和排序接口。
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..state import get_task_manager, get_queue_manager
from .auth import require_auth


router = APIRouter()


# ============ 请求/响应模型 ============

class TaskCreate(BaseModel):
    """创建任务请求"""
    name: str
    command: str
    note: Optional[str] = None


class TaskUpdate(BaseModel):
    """更新任务请求"""
    name: Optional[str] = None
    command: Optional[str] = None
    note: Optional[str] = None


class TaskReorder(BaseModel):
    """重排任务请求"""
    order: List[str]  # 任务ID列表


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    name: str
    command: str
    status: str
    gpu: Optional[List[int]]
    start_time: Optional[str]
    end_time: Optional[str]
    duration: Optional[float]
    error_message: Optional[str]
    log_file: Optional[str]
    note: Optional[str] = None
    can_run: bool = True
    conflict_message: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    pending: List[TaskResponse]
    running: List[TaskResponse]


# ============ 辅助函数 ============

def _save_state():
    """保存工作空间状态"""
    queue_manager = get_queue_manager()
    if queue_manager:
        queue_manager._save_workspace()


# ============ API 端点 ============

@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(_=Depends(require_auth)):
    """获取所有任务"""
    manager = get_task_manager()
    
    # 如果没有加载队列，返回空列表
    if manager is None:
        return {"pending": [], "running": []}
    
    pending = []
    for task in manager.get_pending_tasks():
        task_dict = task.to_dict()
        conflict = manager.check_gpu_conflict(task.id)
        task_dict["can_run"] = conflict is None
        task_dict["conflict_message"] = conflict
        pending.append(task_dict)
    
    running = [task.to_dict() for task in manager.get_running_tasks()]
    
    return {"pending": pending, "running": running}


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, _=Depends(require_auth)):
    """创建新任务"""
    manager = get_task_manager()
    
    if manager is None:
        raise HTTPException(status_code=400, detail="请先添加任务队列")
    
    if not task.name or not task.command:
        raise HTTPException(status_code=400, detail="任务名称和命令不能为空")
    
    new_task = manager.add_task(task.name, task.command, task.note)
    
    # 持久化
    _save_state()
    
    result = new_task.to_dict()
    result["can_run"] = True
    result["conflict_message"] = None
    return result


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, _=Depends(require_auth)):
    """获取单个任务"""
    manager = get_task_manager()
    task = manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    result = task.to_dict()
    conflict = manager.check_gpu_conflict(task_id)
    result["can_run"] = conflict is None
    result["conflict_message"] = conflict
    return result


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task: TaskUpdate, _=Depends(require_auth)):
    """更新任务"""
    manager = get_task_manager()
    
    try:
        updated = manager.update_task(task_id, task.name, task.command, task.note)
        if not updated:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 持久化
        _save_state()
        
        result = updated.to_dict()
        conflict = manager.check_gpu_conflict(task_id)
        result["can_run"] = conflict is None
        result["conflict_message"] = conflict
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, _=Depends(require_auth)):
    """删除任务"""
    manager = get_task_manager()
    
    try:
        success = manager.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 持久化
        _save_state()
        
        return {"success": True, "message": "任务已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/reorder")
async def reorder_tasks(reorder: TaskReorder, _=Depends(require_auth)):
    """重排任务顺序"""
    manager = get_task_manager()
    
    success = manager.reorder_tasks(reorder.order)
    if not success:
        raise HTTPException(status_code=400, detail="无效的任务顺序")
    
    # 持久化
    _save_state()
    
    return {"success": True, "message": "任务顺序已更新"}


@router.get("/history")
async def get_history(limit: int = 50, _=Depends(require_auth)):
    """获取执行历史"""
    manager = get_task_manager()
    
    # 如果没有加载队列，返回空列表
    if manager is None:
        return {"history": []}
    
    history = manager.get_history(limit)
    return {"history": history}  # 已经是 dict 列表


@router.delete("/history")
async def clear_history(_=Depends(require_auth)):
    """清空执行历史"""
    manager = get_task_manager()
    if manager is None:
        return {"success": True, "message": "无历史记录"}
    manager.clear_history()
    
    # 持久化
    _save_state()
    
    return {"success": True, "message": "历史已清空"}


@router.get("/status")
async def get_status(_=Depends(require_auth)):
    """获取当前状态"""
    manager = get_task_manager()
    if manager is None:
        return {"pending_count": 0, "running_count": 0, "queue_running": False}
    return manager.get_status()
