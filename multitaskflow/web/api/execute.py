#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
执行控制 API

提供任务运行、停止等控制接口。
"""

from fastapi import APIRouter, HTTPException

from ..state import get_task_manager


router = APIRouter()


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str):
    """
    运行指定任务
    
    会先检查 GPU 冲突，如果有冲突则返回错误。
    """
    manager = get_task_manager()
    
    if manager is None:
        raise HTTPException(status_code=400, detail="请先添加任务队列")
    
    try:
        task = manager.run_task(task_id)
        return {
            "success": True,
            "message": f"任务 {task.name} 已启动",
            "task": task.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """停止指定任务"""
    manager = get_task_manager()
    
    if manager is None:
        raise HTTPException(status_code=400, detail="请先添加任务队列")
    
    success = manager.stop_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="任务不存在或未在运行")
    
    return {"success": True, "message": "任务已停止"}


@router.post("/stop-all")
async def stop_all():
    """停止所有运行中的任务"""
    manager = get_task_manager()
    if manager is None:
        return {"success": True, "message": "无运行中的任务"}
    manager.stop_all()
    return {"success": True, "message": "所有任务已停止"}


@router.post("/start-queue")
async def start_queue():
    """开始自动队列执行（按顺序执行所有待执行任务）"""
    manager = get_task_manager()
    
    if manager is None:
        return {"success": False, "message": "请先添加任务队列"}
    
    if manager.queue_running:
        return {"success": False, "message": "队列已在运行中"}
    
    pending = manager.get_pending_tasks()
    if not pending:
        return {"success": False, "message": "没有待执行的任务"}
    
    manager.start_queue()
    return {
        "success": True, 
        "message": f"队列已启动，共 {len(pending)} 个任务"
    }


@router.post("/stop-queue")
async def stop_queue():
    """停止队列自动执行（完成当前任务后停止）"""
    manager = get_task_manager()
    if manager is None:
        return {"success": True, "message": "无队列运行"}
    manager.stop_queue()
    return {"success": True, "message": "队列将在当前任务完成后停止"}


@router.get("/queue-status")
async def queue_status():
    """获取队列状态"""
    manager = get_task_manager()
    
    if manager is None:
        return {
            "running": False,
            "pending_count": 0,
            "running_count": 0,
            "main_log_file": None
        }
    
    return {
        "running": manager.queue_running,
        "pending_count": len(manager.get_pending_tasks()),
        "running_count": len(manager.get_running_tasks()),
        "main_log_file": manager.main_log_file
    }


@router.get("/main-log")
async def get_main_log(lines: int = 200):
    """获取主进程日志内容"""
    from pathlib import Path
    
    manager = get_task_manager()
    
    if manager is None:
        return {
            "success": True,
            "content": "请先添加任务队列",
            "log_file": None
        }
    
    log_path = Path(manager.main_log_file)
    
    if not log_path.exists():
        return {
            "success": True,
            "content": "主进程日志正在初始化...",
            "log_file": manager.main_log_file
        }
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # 只返回最后 N 行
        all_lines = content.split('\n')
        if len(all_lines) > lines:
            content = '\n'.join(all_lines[-lines:])
        
        return {
            "success": True,
            "content": content,
            "log_file": manager.main_log_file,
            "total_lines": len(all_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")


@router.post("/reload")
async def reload_tasks():
    """重新加载配置文件（清空并重新加载）"""
    manager = get_task_manager()
    
    if manager is None:
        raise HTTPException(status_code=400, detail="请先添加任务队列")
    
    # 检查是否有运行中的任务
    if manager.get_running_tasks():
        raise HTTPException(
            status_code=400, 
            detail="有任务正在运行，无法重新加载"
        )
    
    # 清空现有任务并重新加载
    manager.tasks.clear()
    manager.task_order.clear()
    count = manager.load_tasks()
    
    return {
        "success": True, 
        "message": f"已重新加载 {count} 个任务"
    }


@router.get("/check-yaml")
async def check_yaml():
    """
    检查 YAML 文件是否有新任务
    
    返回新任务列表及其校验结果，不会自动加载。
    """
    manager = get_task_manager()
    
    if manager is None:
        return {
            "success": True,
            "error": None,
            "total_in_yaml": 0,
            "existing_count": 0,
            "new_tasks": [],
            "valid_count": 0,
            "invalid_count": 0,
            "message": "请先添加任务队列"
        }
    
    result = manager.check_yaml_updates()
    
    valid_count = sum(1 for t in result["new_tasks"] if t["valid"])
    invalid_count = sum(1 for t in result["new_tasks"] if not t["valid"])
    
    return {
        "success": result["error"] is None,
        "error": result["error"],
        "total_in_yaml": result["total_in_yaml"],
        "new_tasks": result["new_tasks"],
        "valid_count": valid_count,
        "invalid_count": invalid_count
    }


@router.post("/load-new-tasks")
async def load_new_tasks():
    """
    加载 YAML 中的新任务
    
    只加载格式正确的新任务，跳过已存在的和无效的任务。
    """
    manager = get_task_manager()
    
    if manager is None:
        return {
            "success": False,
            "message": "请先添加任务队列",
            "loaded": 0,
            "skipped": 0,
            "errors": []
        }
    
    result = manager.load_new_tasks_from_yaml()
    
    message_parts = []
    if result["loaded"] > 0:
        message_parts.append(f"已加载 {result['loaded']} 个新任务")
    if result["skipped"] > 0:
        message_parts.append(f"跳过 {result['skipped']} 个无效任务")
    if not message_parts:
        message_parts.append("没有发现新任务")
    
    return {
        "success": True,
        "message": "，".join(message_parts),
        "loaded": result["loaded"],
        "skipped": result["skipped"],
        "errors": result["errors"]
    }


@router.get("/logs/{task_id}")
async def get_log_content(task_id: str, lines: int = 500):
    """
    获取任务日志内容
    
    Args:
        task_id: 任务ID
        lines: 返回最后多少行（默认500）
    """
    from pathlib import Path
    from ..state import get_queue_manager
    
    queue_manager = get_queue_manager()
    
    if queue_manager is None:
        return {"success": False, "detail": "请先添加任务队列"}
    
    log_file = None
    
    # 在所有队列中查找运行中或待执行任务
    task, queue = queue_manager.find_task_in_all_queues(task_id)
    if task and task.log_file:
        log_file = task.log_file
    else:
        # 在所有队列的历史记录中查找
        task_dict, queue = queue_manager.find_task_in_history(task_id)
        if task_dict:
            log_file = task_dict.get('log_file')
    
    if not log_file:
        raise HTTPException(status_code=404, detail="找不到任务日志")
    
    log_path = Path(log_file)
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="日志文件不存在")
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # 只返回最后 N 行
        all_lines = content.split('\n')
        if len(all_lines) > lines:
            content = '\n'.join(all_lines[-lines:])
        
        return {
            "success": True,
            "log_file": str(log_file),
            "content": content,
            "total_lines": len(all_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")
