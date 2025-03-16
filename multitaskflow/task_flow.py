#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务流管理模块 (Task Flow Manager)

此模块提供了任务队列管理和执行功能，主要用于:
1. 管理多个连续任务的执行
2. 追踪任务状态和执行时间
3. 在任务完成或失败时发送通知
4. 支持动态添加新任务

主要组件:
- Task: 任务类，表示一个可执行的任务
- TaskFlow: 任务流管理器，负责任务的调度和执行

典型用例:
- 深度学习模型的连续训练任务
- 数据处理批处理任务
- 需要顺序执行的脚本集合

使用示例见文件末尾的 __main__ 部分
"""

import logging
import os
import time
import subprocess
import psutil
import json
import requests
import sys
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import yaml
from threading import Thread, Event, Lock
from dotenv import load_dotenv
from queue import Queue
import queue
import signal
import importlib.util

# 检查process_monitor模块是否可导入
if importlib.util.find_spec("multitaskflow.process_monitor") is not None:
    from multitaskflow.process_monitor import ProcessMonitor, Msg_push
else:
    # 尝试从当前目录导入
    try:
        from process_monitor import ProcessMonitor, Msg_push
    except ImportError:
        raise ImportError("无法导入ProcessMonitor模块，请确保process_monitor.py在正确的路径下")

class Task:
    """
    任务类，表示一个可执行的任务
    
    属性:
        name: 任务名称
        command: 要执行的命令
        status: 任务状态
        start_time: 开始时间
        end_time: 结束时间
        return_code: 命令返回值
        duration: 执行时长
    """
    
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    def __init__(self, name: str, command: str, status: str = STATUS_PENDING):
        """
        初始化任务实例
        
        Args:
            name: 任务名称
            command: 要执行的命令行字符串
            status: 初始状态，默认为"pending"
        """
        self.name = name
        self.command = command
        self.status = status
        self.start_time = None
        self.end_time = None
        self.return_code = None
        self.process = None
        self.error_message = None
        self.duration = None
        self.monitor = None

    def to_dict(self) -> Dict[str, Any]:
        """
        将任务转换为字典格式，用于保存到配置文件和生成报告
        
        Returns:
            Dict[str, Any]: 任务的字典表示
        """
        return {
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "start_time": self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            "end_time": self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            "duration": str(self.duration) if self.duration else "未完成",
            "return_code": self.return_code,
            "error_message": self.error_message
        }

    def update_duration(self):
        """
        更新任务运行时长
        """
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time

    def start(self):
        """
        开始任务
        """
        self.status = self.STATUS_RUNNING
        self.start_time = datetime.now()

    def complete(self, return_code: int, error_message: str = None):
        """
        完成任务
        
        Args:
            return_code: 返回码，0表示成功
            error_message: 错误信息，失败时提供
        """
        self.end_time = datetime.now()
        self.return_code = return_code
        self.error_message = error_message
        self.status = self.STATUS_COMPLETED if return_code == 0 else self.STATUS_FAILED
        self.update_duration()

class TaskFlow:
    """
    任务流管理器，负责任务的调度和执行
    
    任务流管理器可以从配置文件加载任务，按顺序执行任务，
    并在任务完成时发送通知。支持动态添加新任务和中断处理。
    
    属性:
        tasks: 任务列表
        total_tasks: 任务总数
        completed_tasks: 已完成任务数
        failed_tasks: 失败任务数
        pending_tasks: 等待任务数
    """
    
    TASK_DIVIDER = "=" * 50
    
    def __init__(self, config_path: str):
        """
        初始化任务流管理器
        
        Args:
            config_path: 任务配置文件路径
        """
        self.config_path = config_path
        self.tasks: List[Task] = []
        self.logger = self._setup_logger()
        self.task_queue = Queue()
        self.running = False
        self.task_lock = Lock()
        self.stop_event = Event()
        self.start_time = None
        self.end_time = None
        
        # 初始化任务计数器
        self._reset_task_counters()
        
        self.logger.info(self.TASK_DIVIDER)
        self.logger.info("任务流管理器初始化...")
        self.load_tasks()
        self.logger.info(self.TASK_DIVIDER)

    def _reset_task_counters(self):
        """重置任务计数器"""
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.pending_tasks = 0

    def _update_task_counters(self):
        """更新任务计数器"""
        self._reset_task_counters()
        self.total_tasks = len(self.tasks)
        for task in self.tasks:
            if task.status == Task.STATUS_COMPLETED:
                self.completed_tasks += 1
            elif task.status == Task.STATUS_FAILED:
                self.failed_tasks += 1
            elif task.status == Task.STATUS_PENDING:
                self.pending_tasks += 1

    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器
        
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        logger = logging.getLogger("TaskFlow")
        logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        # 文件处理器
        fh = logging.FileHandler(
            f"logs/taskflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        )
        fh.setLevel(logging.INFO)
        
        # 控制台处理器
        ch = logging.StreamHandler(sys.stdout)  # 明确指定输出到stdout
        ch.setLevel(logging.INFO)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger

    def load_tasks(self):
        """
        从配置文件加载初始任务
        
        配置文件应为YAML格式，包含任务列表，每个任务需指定名称和命令
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                task_list = yaml.safe_load(f)
                
            if not isinstance(task_list, list):
                raise ValueError("配置文件格式错误：应该是任务列表")
                
            for task_config in task_list:
                task = Task(
                    name=task_config['name'],
                    command=task_config['command'],
                    status=task_config.get('status', 'pending')
                )
                self.add_task(task)
                
            self.logger.info(f"已加载 {len(self.tasks)} 个初始任务")
        except Exception as e:
            self.logger.error(f"加载任务配置失败: {str(e)}")
            raise

    def add_task(self, task: Task):
        """
        添加新任务到队列
        
        Args:
            task: 要添加的任务实例
        """
        with self.task_lock:
            self.tasks.append(task)
            self.task_queue.put(task)
            self.total_tasks += 1
        self.logger.info(f"新任务已添加: {task.name}")

    def add_task_by_config(self, name: str, command: str):
        """
        通过参数添加新任务
        
        Args:
            name: 任务名称
            command: 要执行的命令
            
        Returns:
            Task: 新添加的任务实例
        """
        task = Task(name=name, command=command)
        self.add_task(task)
        return task

    def format_duration(self, duration: timedelta) -> str:
        """
        将时间间隔转换为中文格式的天时分秒
        
        Args:
            duration: 时间间隔
            
        Returns:
            str: 格式化的时间字符串
        """
        total_seconds = int(duration.total_seconds())
        days = total_seconds // (24 * 3600)
        remaining_seconds = total_seconds % (24 * 3600)
        hours = remaining_seconds // 3600
        remaining_seconds %= 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0 or days > 0:
            parts.append(f"{hours}时")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}分")
        parts.append(f"{seconds}秒")
        
        return "".join(parts)

    def get_duration(self) -> str:
        """
        获取总运行时长
        
        Returns:
            str: 格式化的时间字符串
        """
        if not self.start_time:
            return "0秒"
        duration = datetime.now() - self.start_time
        return self.format_duration(duration)

    def generate_summary(self) -> str:
        """
        生成详细的任务执行报告
        
        Returns:
            str: 任务执行报告文本
        """
        if self.start_time:
            self.end_time = datetime.now()
            total_duration = self.end_time - self.start_time
        else:
            total_duration = timedelta(0)

        summary = f"""
        【任务流管理器执行报告】
        ====================
        执行开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else '未开始'}
        执行结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else '未结束'}
        总运行时长: {self.format_duration(total_duration)}
        任务统计: {self.total_tasks}个任务 (总数)
        状态分布: 成功 {self.completed_tasks}个 | 失败 {self.failed_tasks}个 | 等待 {self.pending_tasks}个
        """
        # 只有当有失败任务时才显示失败任务列表
        failed_tasks = [task for task in self.tasks if task.status == "failed"]
        if failed_tasks:
            summary += "\n失败任务列表:\n"
            for task in failed_tasks:
                summary += f"""
                {'-' * 40}
                任务名称: {task.name}
                执行命令: {task.command}
                执行时长: {self.format_duration(task.duration) if task.duration else '未完成'}
                错误信息: {task.error_message or '未知错误'}
                """
        return summary

    def execute_task(self, task: Task) -> bool:
        """
        执行单个任务
        
        Args:
            task: 要执行的任务
            
        Returns:
            bool: 任务是否成功执行
        """
        self.logger.info(self.TASK_DIVIDER)
        self.logger.info(f"开始执行任务: {task.name}")
        self.logger.info(f"执行命令: {task.command}")
        
        task.start()
        
        try:
            # 启动进程，保持原始输出到终端
            task.process = subprocess.Popen(
                task.command,
                shell=True,
                bufsize=1,
                universal_newlines=True,
                stdout=None,  # 保持原始输出到终端
                stderr=None   # 保持原始输出到终端
            )
            
            # 启动进程监控
            task.monitor = ProcessMonitor(
                process_name=task.name,
                process_cmd=task.command,
                logger=self.logger,
                start_time=task.start_time
            )
            task.monitor.start()
            
            # 等待进程完成
            return_code = task.process.wait()  # 等待进程完成
            
            # 更新任务状态
            task.complete(return_code)
            
            # 更新监控器状态（消息发送由monitor自己处理）
            if task.monitor:
                task.monitor.set_result(
                    return_code,
                    "执行失败" if return_code != 0 else None
                )

            if task.status == Task.STATUS_COMPLETED:
                self.logger.info(f"任务执行完成: {task.name}")
                return True
            else:
                self.logger.error(f"任务执行失败: {task.name}")
                self.logger.error(f"返回值: {return_code}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            task.complete(-1, error_msg)
            
            # 更新监控器状态（消息发送由monitor自己处理）
            if task.monitor:
                task.monitor.set_result(-1, error_msg)
                
            self.logger.error(f"任务执行异常: {task.name}")
            self.logger.error(f"异常信息: {error_msg}")
            return False
        finally:
            self._update_task_counters()
            self.logger.info(self.TASK_DIVIDER)

    def check_new_tasks(self):
        """
        检查配置文件中是否有新任务
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                task_list = yaml.safe_load(f)
                
            if not isinstance(task_list, list):
                return
            
            existing_tasks = {task.name for task in self.tasks}
            
            for task_config in task_list:
                task_name = task_config['name']
                if task_name not in existing_tasks:
                    self.logger.info(f"发现新任务: {task_name}")
                    task = Task(
                        name=task_config['name'],
                        command=task_config['command'],
                        status=task_config.get('status', 'pending')
                    )
                    self.add_task(task)
                    
        except Exception as e:
            self.logger.error(f"检查新任务时出错: {str(e)}")

    def run(self):
        """
        运行任务流管理器，开始执行任务队列
        """
        self.running = True
        self.start_time = datetime.now()
        self.logger.info("任务流管理器启动")
        
        last_task_time = datetime.now()
        
        while not self.stop_event.is_set():
            try:
                self.check_new_tasks()
                task = self.task_queue.get(timeout=1)
                last_task_time = datetime.now()
                self.execute_task(task)
            except queue.Empty:
                if (datetime.now() - last_task_time).total_seconds() > 60:
                    self.check_new_tasks()
                    if self.task_queue.empty():
                        self.logger.info("1分钟内无新任务，准备停止任务流管理器")
                        self.stop()
                continue
            except Exception as e:
                self.logger.error(f"执行任务时出现异常: {str(e)}")
                continue

        self.logger.info("任务流管理器已停止")
        self.running = False

    def stop(self):
        """
        停止任务流管理器并发送总结报告
        """
        self.stop_event.set()
        self.logger.info("正在停止任务流管理器...")
        
        # 等待当前任务完成
        if self.running:
            self.end_time = datetime.now()
            summary = self.generate_summary()
            self.logger.info("发送任务总结报告...")
            self.logger.info(summary)  # 在日志中也记录摘要
            
            # 发送总结报告
            Msg_push(
                title="任务流管理器执行报告",
                content=summary,
                logger=self.logger
            )

    def is_running(self) -> bool:
        """
        返回任务流管理器是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        return self.running

if __name__ == "__main__":
    """
    任务流管理器的使用示例
    
    此示例展示了如何初始化和运行任务流管理器，
    包括信号处理和异常捕获。
    """
    def signal_handler(signum, frame):
        """处理终止信号"""
        print("\n接收到终止信号，正在优雅地停止任务流管理器...")
        if 'manager' in locals() and manager.is_running():
            manager.stop()
        
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 检查是否存在配置文件，如果不存在则创建示例配置
        config_path = "examples/tasks.yaml"
        if not os.path.exists(os.path.dirname(config_path)):
            os.makedirs(os.path.dirname(config_path))
            
        if not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write("""# 任务流配置示例
# 每个任务包含名称和要执行的命令
# 任务将按照列表顺序依次执行

- name: "示例任务1"
  command: "echo '这是第一个任务' && sleep 2"
  status: "pending"

- name: "示例任务2" 
  command: "echo '这是第二个任务' && sleep 3"
  status: "pending"
""")
            print(f"已创建示例配置文件: {config_path}")
        
        # 创建并启动任务流管理器
        manager = TaskFlow(config_path)
        manager_thread = Thread(target=manager.run)
        manager_thread.start()
        manager_thread.join()
    except Exception as e:
        print(f"任务流管理器运行出错: {str(e)}")
        if 'manager' in locals() and manager.is_running():
            manager.stop()
    finally:
        if 'manager' in locals() and manager.is_running():
            manager.stop()
            if 'manager_thread' in locals() and manager_thread.is_alive():
                manager_thread.join() 