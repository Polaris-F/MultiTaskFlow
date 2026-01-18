"""
MultiTaskFlow - 多任务流管理工具

此工具用于管理和监控多个连续任务的执行，特别适用于深度学习训练场景。
支持任务状态监控、执行时间统计和消息推送通知功能。

主要模块:
- task_flow: 任务流管理器，用于按顺序执行多个任务
- process_monitor: 进程监控工具，用于监控任务执行并发送通知

作者: LHF
许可证: MIT
版本: 0.1.5
"""

from .task_flow import TaskFlow, Task
from .process_monitor import ProcessMonitor, Msg_push

__version__ = '1.0.0'
__author__ = 'LHF'

__all__ = [
    'TaskFlow',
    'Task',
    'ProcessMonitor',
    'Msg_push'
] 