#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全局状态管理

存储全局的队列管理器和任务管理器实例，避免循环导入。
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import TaskManager
    from .queue_manager import QueueManager

# 全局队列管理器实例（多队列模式）
_queue_manager: Optional["QueueManager"] = None

# 全局任务管理器实例（单队列兼容模式）
_task_manager: Optional["TaskManager"] = None

# 当前活动队列 ID（用于单队列模式兼容）
_current_queue_id: Optional[str] = None


def get_queue_manager() -> "QueueManager":
    """获取队列管理器实例"""
    global _queue_manager
    if _queue_manager is None:
        raise RuntimeError("QueueManager 未初始化，请先调用 set_queue_manager()")
    return _queue_manager


def set_queue_manager(manager: "QueueManager"):
    """设置队列管理器实例"""
    global _queue_manager
    _queue_manager = manager


def get_task_manager(queue_id: str = None) -> Optional["TaskManager"]:
    """
    获取任务管理器实例
    
    Args:
        queue_id: 队列 ID，如果不指定则使用当前活动队列
        
    Returns:
        TaskManager 实例，如果没有队列则返回 None
    """
    global _task_manager, _queue_manager, _current_queue_id
    
    # 单队列兼容模式
    if _task_manager is not None:
        return _task_manager
    
    # 多队列模式
    if _queue_manager is not None:
        qid = queue_id or _current_queue_id
        if qid:
            manager = _queue_manager.get_queue(qid)
            if manager:
                return manager
        
        # 如果没有指定队列，返回第一个队列
        queues = list(_queue_manager.queues.values())
        if queues:
            return queues[0]
    
    # 没有队列时返回 None 而不是抛出异常
    return None


def set_task_manager(manager: "TaskManager"):
    """设置任务管理器实例（单队列兼容模式）"""
    global _task_manager
    _task_manager = manager


def set_current_queue(queue_id: str):
    """设置当前活动队列 ID"""
    global _current_queue_id
    _current_queue_id = queue_id


def get_current_queue_id() -> Optional[str]:
    """获取当前活动队列 ID"""
    global _current_queue_id, _queue_manager
    
    if _current_queue_id:
        return _current_queue_id
    
    # 如果未设置，返回第一个队列 ID
    if _queue_manager and _queue_manager.queues:
        return list(_queue_manager.queues.keys())[0]
    
    return None


def clear_state():
    """清除所有全局状态"""
    global _task_manager, _queue_manager, _current_queue_id
    _task_manager = None
    _queue_manager = None
    _current_queue_id = None


# 兼容旧代码
def clear_task_manager():
    """清除任务管理器实例"""
    global _task_manager
    _task_manager = None
