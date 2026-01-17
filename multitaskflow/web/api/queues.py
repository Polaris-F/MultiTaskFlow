#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
队列管理 API

提供多队列的增删查接口和当前队列切换。
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..state import get_queue_manager, set_current_queue, get_current_queue_id
from .auth import require_auth


router = APIRouter()


# ============ 请求/响应模型 ============

class QueueCreate(BaseModel):
    """创建队列请求"""
    name: str
    yaml_path: str


class QueueResponse(BaseModel):
    """队列信息响应"""
    id: str
    name: str
    yaml_path: str
    created_at: str
    status: Optional[dict] = None


# ============ API 端点 ============

@router.get("/queues")
async def get_queues(_=Depends(require_auth)):
    """获取所有队列"""
    manager = get_queue_manager()
    queues = manager.get_all_queues()
    current_id = get_current_queue_id()
    return {
        "queues": queues,
        "current_queue_id": current_id
    }


@router.post("/queues")
async def create_queue(queue: QueueCreate, _=Depends(require_auth)):
    """添加新队列"""
    manager = get_queue_manager()
    
    if not queue.name or not queue.yaml_path:
        raise HTTPException(status_code=400, detail="队列名称和 YAML 路径不能为空")
    
    try:
        config = manager.add_queue(queue.name, queue.yaml_path)
        # 自动切换到新队列
        set_current_queue(config['id'])
        return {"success": True, "queue": config}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加队列失败: {str(e)}")


@router.delete("/queues/{queue_id}")
async def delete_queue(queue_id: str, _=Depends(require_auth)):
    """移除队列（不删除文件）"""
    manager = get_queue_manager()
    
    success = manager.remove_queue(queue_id)
    if not success:
        raise HTTPException(status_code=404, detail="队列不存在")
    
    return {"success": True, "message": "队列已移除"}


@router.get("/queues/{queue_id}")
async def get_queue(queue_id: str, _=Depends(require_auth)):
    """获取队列信息"""
    manager = get_queue_manager()
    
    queue = manager.get_queue(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    
    config = manager.queue_configs.get(queue_id, {})
    return {
        **config,
        "status": {
            "queue_running": queue.queue_running,
            "pending_count": len(queue.get_pending_tasks()),
            "running_count": len(queue.get_running_tasks()),
        }
    }


@router.post("/queues/{queue_id}/select")
async def select_queue(queue_id: str, _=Depends(require_auth)):
    """切换当前活动队列"""
    manager = get_queue_manager()
    
    queue = manager.get_queue(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    
    set_current_queue(queue_id)
    return {"success": True, "current_queue_id": queue_id}


@router.get("/global/gpu-usage")
async def get_global_gpu_usage(_=Depends(require_auth)):
    """获取跨队列 GPU 使用情况"""
    manager = get_queue_manager()
    usage = manager.get_global_gpu_usage()
    return {"gpu_usage": usage}


@router.get("/queues/{queue_id}/cross-conflict/{task_id}")
async def check_cross_conflict(queue_id: str, task_id: str, _=Depends(require_auth)):
    """检查跨队列 GPU 冲突"""
    manager = get_queue_manager()
    
    conflict = manager.check_cross_queue_conflict(queue_id, task_id)
    return {
        "has_conflict": conflict is not None,
        "message": conflict
    }
