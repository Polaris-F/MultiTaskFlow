#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
执行控制 API

提供任务运行、停止等控制接口。
"""

from fastapi import APIRouter, HTTPException, Depends

from ..state import get_task_manager
from .auth import require_auth


router = APIRouter()


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str, _=Depends(require_auth)):
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
async def stop_task(task_id: str, _=Depends(require_auth)):
    """停止指定任务"""
    manager = get_task_manager()
    
    if manager is None:
        raise HTTPException(status_code=400, detail="请先添加任务队列")
    
    success = manager.stop_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="任务不存在或未在运行")
    
    return {"success": True, "message": "任务已停止"}


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str, _=Depends(require_auth)):
    """
    重试任务 - 将失败/停止的任务重置为 pending 状态并加入队列末尾
    """
    from ..state import get_queue_manager
    
    # 尝试在所有队列中查找任务
    qm = get_queue_manager()
    manager = None
    
    if qm:
        # 多队列模式：遍历所有队列查找任务
        for queue in qm.queues.values():
            if queue.get_task(task_id):
                manager = queue
                break
    
    if manager is None:
        # 回退到当前队列
        manager = get_task_manager()
    
    if manager is None:
        raise HTTPException(status_code=400, detail="请先添加任务队列")
    
    try:
        task = manager.retry_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 持久化状态
        if qm:
            qm._save_workspace()
        
        return {
            "success": True,
            "message": f"任务 {task.name} 已加入队列末尾",
            "task": task.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop-all")
async def stop_all(_=Depends(require_auth)):
    """停止所有运行中的任务"""
    manager = get_task_manager()
    if manager is None:
        return {"success": True, "message": "无运行中的任务"}
    manager.stop_all()
    return {"success": True, "message": "所有任务已停止"}


@router.post("/start-queue")
async def start_queue(_=Depends(require_auth)):
    """开始自动队列执行（按顺序执行所有待执行任务）"""
    from ..state import get_queue_manager
    manager = get_task_manager()
    
    if manager is None:
        return {"success": False, "message": "请先添加任务队列"}
    
    if manager.queue_running:
        return {"success": False, "message": "队列已在运行中"}
    
    pending = manager.get_pending_tasks()
    running = manager.get_running_tasks()
    
    # 允许启动队列，即使没有待执行任务（可能有运行中的任务，或后续会添加任务）
    manager.start_queue()
    
    # 保存队列状态
    queue_manager = get_queue_manager()
    if queue_manager:
        queue_manager._save_workspace()
    
    if pending:
        return {
            "success": True, 
            "message": f"队列已启动，共 {len(pending)} 个待执行任务"
        }
    elif running:
        return {
            "success": True, 
            "message": f"队列已启动，当前有 {len(running)} 个运行中任务"
        }
    else:
        return {
            "success": True, 
            "message": "队列已启动，等待添加任务"
        }


@router.post("/stop-queue")
async def stop_queue(_=Depends(require_auth)):
    """停止队列自动执行（完成当前任务后停止）"""
    from ..state import get_queue_manager
    manager = get_task_manager()
    if manager is None:
        return {"success": True, "message": "无队列运行"}
    manager.stop_queue()
    
    # 保存队列状态
    queue_manager = get_queue_manager()
    if queue_manager:
        queue_manager._save_workspace()
    
    return {"success": True, "message": "队列将在当前任务完成后停止"}


@router.get("/queue-status")
async def queue_status(_=Depends(require_auth)):
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
async def get_main_log(lines: int = 200, _=Depends(require_auth)):
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
        from ..ws import clean_progress_bar_output
        
        with open(log_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            content = f.read()
        
        # 清理进度条输出
        content = clean_progress_bar_output(content)
        
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
async def reload_tasks(_=Depends(require_auth)):
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
async def check_yaml(_=Depends(require_auth)):
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
async def load_new_tasks(_=Depends(require_auth)):
    """
    加载 YAML 中的新任务
    
    只加载格式正确的新任务，跳过已存在的和无效的任务。
    """
    from ..state import get_queue_manager
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
    
    # 保存状态到工作空间（持久化新加载的任务）
    if result["loaded"] > 0:
        queue_manager = get_queue_manager()
        if queue_manager:
            queue_manager._save_workspace()
    
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


from pydantic import BaseModel
from typing import List

class SelectedTask(BaseModel):
    name: str
    command: str
    note: str = ""

class LoadSelectedTasksRequest(BaseModel):
    tasks: List[SelectedTask]

@router.post("/load-selected-tasks")
async def load_selected_tasks(request: LoadSelectedTasksRequest, _=Depends(require_auth)):
    """
    加载用户选择的任务
    
    只加载用户在弹窗中勾选的任务。
    """
    from ..state import get_queue_manager
    from ..manager import Task, TaskStatus, parse_gpu_from_command
    
    manager = get_task_manager()
    
    if manager is None:
        return {
            "success": False,
            "message": "请先添加任务队列",
            "loaded": 0,
            "errors": []
        }
    
    loaded = 0
    errors = []
    skipped = 0
    
    # 【重要】构建完整的已存在任务名称集合（包括当前队列和历史记录）
    existing_names = {t.name for t in manager.get_all_tasks()}
    existing_names.update(getattr(manager, '_loaded_task_names', set()))
    # 从历史记录获取已执行任务名称
    history_names = {h.get('name') for h in manager.history_manager.items if h.get('name')}
    existing_names.update(history_names)
    
    for task_data in request.tasks:
        if not task_data.name or not task_data.command:
            errors.append(f"{task_data.name or '未命名'}: 缺少名称或命令")
            continue
        
        # 【新增】检查是否重复任务
        if task_data.name in existing_names:
            errors.append(f"{task_data.name}: 任务已存在（队列或历史中），已跳过")
            skipped += 1
            continue
        
        with manager._lock:
            task_id = manager._generate_task_id()
            task = Task(
                id=task_id,
                name=task_data.name,
                command=task_data.command,
                note=task_data.note or None,
                status=TaskStatus.PENDING,
                gpu=parse_gpu_from_command(task_data.command)
            )
            manager.tasks[task_id] = task
            manager.task_order.append(task_id)
            
            # 更新已加载名称集合
            if not hasattr(manager, '_loaded_task_names'):
                manager._loaded_task_names = set()
            manager._loaded_task_names.add(task_data.name)
            
            loaded += 1
            manager.logger.info(f"加载选中任务: {task_data.name} (ID: {task_id})")
    
    # 保存状态
    if loaded > 0:
        queue_manager = get_queue_manager()
        if queue_manager:
            queue_manager._save_workspace()
    
    # 构建返回消息
    message_parts = []
    if loaded > 0:
        message_parts.append(f"已加载 {loaded} 个任务")
    if skipped > 0:
        message_parts.append(f"跳过 {skipped} 个重复任务")
    if not message_parts:
        message_parts.append("没有任务被加载")
    
    return {
        "success": True,
        "message": "，".join(message_parts),
        "loaded": loaded,
        "skipped": skipped,
        "errors": errors
    }

@router.get("/logs/{task_id}")
async def get_log_content(task_id: str, lines: int = 500, _=Depends(require_auth)):
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
        from ..ws import clean_progress_bar_output
        
        with open(log_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            content = f.read()
        
        # 清理进度条输出
        content = clean_progress_bar_output(content)
        
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
