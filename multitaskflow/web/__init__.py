"""
MultiTaskFlow Web 模块

提供 Web UI 管理任务流的功能。
"""

from .server import create_app, run_server

__all__ = ['create_app', 'run_server']
