#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI 服务主入口

提供 Web UI 和 REST API 服务。
支持多队列模式和单 YAML 兼容模式。
"""

import os
import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from multitaskflow import __version__
from .manager import TaskManager
from .queue_manager import QueueManager
from .state import (
    set_task_manager, set_queue_manager, clear_state, 
    get_task_manager, get_queue_manager
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    config_path = getattr(app.state, 'config_path', None)
    workspace_dir = getattr(app.state, 'workspace_dir', None)
    
    # 确定工作空间目录
    if not workspace_dir:
        if config_path:
            # 使用 YAML 所在目录作为工作空间
            workspace_dir = str(Path(config_path).resolve().parent)
        else:
            # 纯 Web 模式：使用当前目录作为工作空间
            workspace_dir = str(Path.cwd())
    
    # 创建队列管理器
    queue_manager = QueueManager(workspace_dir)
    set_queue_manager(queue_manager)
    
    # 如果指定了 YAML，自动添加到队列
    if config_path:
        try:
            queue_manager.add_single_yaml(str(Path(config_path).resolve()))
        except ValueError as e:
            # YAML 已存在于工作空间中，忽略
            pass
    
    yield
    
    # 关闭时只停止队列调度，不终止运行中的任务进程
    # 任务进程是独立进程，WebUI 重启后可恢复监控
    try:
        queue_manager = get_queue_manager()
        for queue in queue_manager.queues.values():
            queue.stop_queue()  # 停止队列自动执行
            # 不再调用 stop_all()，让任务进程继续运行
    except RuntimeError:
        pass
    clear_state()


def create_app(config_path: str = None, workspace_dir: str = None) -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Args:
        config_path: 任务配置文件路径（单队列模式）
        workspace_dir: 工作空间目录（多队列模式）
    
    Returns:
        FastAPI 应用实例
    """
    app = FastAPI(
        title="MultiTaskFlow",
        description="多任务流管理工具 Web UI",
        version=__version__,
        lifespan=lifespan
    )
    
    # 保存配置
    if config_path:
        app.state.config_path = config_path
    if workspace_dir:
        app.state.workspace_dir = workspace_dir
    
    # 延迟导入 API 路由（避免循环导入）
    from .api import tasks as tasks_api
    from .api import execute as execute_api
    from .api import queues as queues_api
    from .api import auth as auth_api
    from .api import notification as notification_api
    from . import ws as ws_api
    
    # 注册 API 路由
    app.include_router(auth_api.router, prefix="/api", tags=["auth"])
    app.include_router(tasks_api.router, prefix="/api", tags=["tasks"])
    app.include_router(execute_api.router, prefix="/api", tags=["execute"])
    app.include_router(queues_api.router, prefix="/api", tags=["queues"])
    app.include_router(notification_api.router, prefix="/api", tags=["notification"])
    app.include_router(ws_api.router, tags=["websocket"])
    
    # 静态文件 - 优先使用 dist 目录（Vite 构建输出）
    static_dir = Path(__file__).parent / "static"
    dist_dir = static_dir / "dist"
    
    if dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")
    
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/")
    async def root():
        """返回首页"""
        # 优先返回 Vite 构建的 index.html
        dist_index = dist_dir / "index.html"
        if dist_index.exists():
            return FileResponse(str(dist_index))
        
        # 回退到旧版 index.html
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "MultiTaskFlow Web UI", "status": "running"}
    
    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "ok"}
    
    return app


def run_server(
    config_path: str = None,
    workspace_dir: str = None,
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False
):
    """
    启动 Web 服务器
    
    Args:
        config_path: 任务配置文件路径（单队列模式）
        workspace_dir: 工作空间目录（多队列模式）
        host: 服务器地址
        port: 服务器端口
        reload: 是否启用热重载
    """
    app = create_app(config_path, workspace_dir)
    
    if config_path:
        mode = "单队列模式 (自动加载 YAML)"
        path_info = config_path
    elif workspace_dir:
        mode = "多队列模式 (通过网页添加队列)"
        path_info = f"工作空间: {workspace_dir}"
    else:
        mode = "纯 Web 模式 (通过网页添加队列)"
        path_info = f"工作空间: {Path.cwd()}"
    
    print(f"\n{'='*60}")
    print(f"  MultiTaskFlow Web UI v{__version__}")
    print(f"  模式: {mode}")
    print(f"  访问地址: http://{host}:{port}")
    print(f"  {path_info}")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MultiTaskFlow Web Server")
    parser.add_argument("config", nargs="?", help="任务配置文件路径（单队列模式）")
    parser.add_argument("--workspace", "-w", help="工作空间目录（多队列模式）")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=8080, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载")
    
    args = parser.parse_args()
    
    if not args.config and not args.workspace:
        # 无参数时使用当前目录作为工作空间
        args.workspace = str(Path.cwd())
    
    run_server(args.config, args.workspace, args.host, args.port, args.reload)
