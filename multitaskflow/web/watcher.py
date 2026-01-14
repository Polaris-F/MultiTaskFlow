#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YAML 文件监控模块

监控任务配置文件变化，自动加载新增任务。
"""

import os
import time
import threading
import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger("FileWatcher")


class YAMLFileHandler(FileSystemEventHandler):
    """YAML 文件变化处理器"""
    
    def __init__(self, config_path: Path, callback: Callable):
        """
        初始化处理器
        
        Args:
            config_path: 监控的配置文件路径
            callback: 文件变化时的回调函数
        """
        self.config_path = config_path
        self.callback = callback
        self.last_modified = 0
        self.debounce_seconds = 1.0  # 防抖时间
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        # 检查是否是目标文件
        event_path = Path(event.src_path).resolve()
        if event_path != self.config_path.resolve():
            return
        
        # 防抖：避免短时间内多次触发
        current_time = time.time()
        if current_time - self.last_modified < self.debounce_seconds:
            return
        self.last_modified = current_time
        
        logger.info(f"检测到配置文件变化: {self.config_path}")
        
        try:
            self.callback()
        except Exception as e:
            logger.error(f"处理文件变化时出错: {e}")


class ConfigWatcher:
    """配置文件监控器"""
    
    def __init__(self, config_path: str, on_change: Callable):
        """
        初始化监控器
        
        Args:
            config_path: 配置文件路径
            on_change: 变化回调函数
        """
        self.config_path = Path(config_path).resolve()
        self.on_change = on_change
        self.observer: Optional[Observer] = None
        self._running = False
    
    def start(self):
        """启动监控"""
        if self._running:
            return
        
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return
        
        # 创建观察者
        self.observer = Observer()
        
        # 创建事件处理器
        handler = YAMLFileHandler(self.config_path, self.on_change)
        
        # 监控配置文件所在目录
        watch_dir = str(self.config_path.parent)
        self.observer.schedule(handler, watch_dir, recursive=False)
        
        # 启动观察者
        self.observer.start()
        self._running = True
        
        logger.info(f"开始监控配置文件: {self.config_path}")
    
    def stop(self):
        """停止监控"""
        if not self._running:
            return
        
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
        
        self._running = False
        logger.info("已停止配置文件监控")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
