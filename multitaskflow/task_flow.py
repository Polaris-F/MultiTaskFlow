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
from pathlib import Path
import yaml
from threading import Thread, Event, Lock
from dotenv import load_dotenv, find_dotenv
from queue import Queue
import queue
import signal
import importlib.util
import inspect

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
    STATUS_SKIPPED = "skipped"  # 跳过的任务

    def __init__(self, name: str, command: str, status: str = STATUS_PENDING, env: Dict[str, str] = None):
        """
        初始化任务实例
        
        Args:
            name: 任务名称
            command: 要执行的命令行字符串
            status: 初始状态，默认为"pending"
            env: 任务级环境变量字典，可选
        """
        self.name = name
        self.command = command
        self.status = status
        self.env = env or {}  # 任务级环境变量
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
        self.config_dir = Path(config_path).parent  # 记录配置文件所在目录
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
        
        # 用于跟踪环境变量变化
        self._last_env_info = None
        
        self.logger.info(self.TASK_DIVIDER)
        self.logger.info("任务流管理器初始化...")
        
        # 首次加载环境变量并显示配置
        env_info = self._load_env()
        self._show_env_config(env_info)
        self._last_env_info = env_info
        
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
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        log_dir = self.config_dir / "logs"
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            
        # 文件处理器
        fh = logging.FileHandler(
            str(log_dir / f"taskflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
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

    def _load_env(self) -> Dict[str, Any]:
        """
        按优先级加载环境变量文件
        
        优先级顺序：
        1. 配置文件同目录的 .env
        2. 当前工作目录的 .env
        3. 向上递归查找的 .env
        
        Returns:
            Dict: 包含加载信息的字典 {
                'env_file': 加载的.env文件路径或None,
                'token': MSG_PUSH_TOKEN的值或None,
                'silent_mode': MTF_SILENT_MODE的值
            }
        """
        env_file = None
        
        # 1. 配置文件同目录
        config_dir_env = self.config_dir / ".env"
        if config_dir_env.exists():
            load_dotenv(config_dir_env, override=True)
            env_file = str(config_dir_env)
            self.logger.debug(f"环境变量加载: {config_dir_env}")
        
        # 2. 当前工作目录
        elif (cwd_env := Path.cwd() / ".env").exists():
            load_dotenv(cwd_env, override=True)
            env_file = str(cwd_env)
            self.logger.debug(f"环境变量加载: {cwd_env}")
        
        # 3. 向上递归查找
        elif (found_env := find_dotenv()):
            load_dotenv(found_env, override=True)
            env_file = found_env
            self.logger.debug(f"环境变量加载: {found_env}")
        
        # 读取环境变量
        token = os.getenv('MSG_PUSH_TOKEN')
        silent_mode = os.getenv('MTF_SILENT_MODE', 'false')
        
        return {
            'env_file': env_file,
            'recommended_path': str(config_dir_env),
            'token': token,
            'silent_mode': silent_mode
        }

    def _show_env_config(self, env_info: Dict[str, Any]):
        """
        显示环境变量配置信息（带颜色高亮）
        
        Args:
            env_info: _load_env() 返回的环境变量信息字典
        """
        # 尝试导入 colorama
        try:
            from colorama import Fore, Style, init
            init(autoreset=True)
            use_color = True
        except ImportError:
            # 如果没有安装 colorama，使用普通文本
            use_color = False
            if not hasattr(self, '_colorama_warning_shown'):
                self.logger.warning("未安装 colorama 库，使用普通文本显示。可运行 'pip install colorama' 启用彩色输出")
                self._colorama_warning_shown = True
            # 定义空的颜色代码
            class Fore:
                GREEN = YELLOW = RED = CYAN = MAGENTA = ""
            class Style:
                RESET_ALL = BRIGHT = ""
        
        divider = "=" * 60
        print(f"\n{divider}")
        
        # 标题：区分全局配置和任务级配置
        is_task_env = env_info.get('task_env', False)
        if is_task_env:
            if use_color:
                print(f"{'[环境变量配置检查 - 任务级配置]':^60}".replace('[环境变量配置检查 - 任务级配置]', f'{Fore.MAGENTA}[环境变量配置检查 - 任务级配置]{Style.RESET_ALL}'))
            else:
                print(f"{'[环境变量配置检查 - 任务级配置]':^60}")
        else:
            print(f"{'[环境变量配置检查]':^60}")
        
        print(divider)
        
        # 显示 .env 文件位置
        if env_info['env_file']:
            if use_color:
                print(f"  .env 文件: {Fore.GREEN}{env_info['env_file']}{Style.RESET_ALL}")
            else:
                print(f"  .env 文件: {env_info['env_file']}")
        else:
            if use_color:
                print(f"  .env 文件: {Fore.RED}未找到{Style.RESET_ALL}")
                print(f"  推荐位置: {Fore.YELLOW}{env_info['recommended_path']}{Style.RESET_ALL}")
            else:
                print(f"  .env 文件: 未找到")
                print(f"  推荐位置: {env_info['recommended_path']}")
        
        # 显示 MSG_PUSH_TOKEN
        token = env_info['token']
        if token:
            # 脱敏显示：前6位...后6位
            if len(token) > 12:
                masked_token = f"{token[:6]}...{token[-6:]}"
            else:
                masked_token = f"{token[:3]}...{token[-3:]}" if len(token) > 6 else "***"
            
            if use_color:
                print(f"  MSG_PUSH_TOKEN: {Fore.GREEN}{masked_token}{Style.RESET_ALL} {Fore.CYAN}(已配置){Style.RESET_ALL}")
            else:
                print(f"  MSG_PUSH_TOKEN: {masked_token} (已配置)")
        else:
            if use_color:
                print(f"  MSG_PUSH_TOKEN: {Fore.RED}❌ 未设置{Style.RESET_ALL}")
            else:
                print(f"  MSG_PUSH_TOKEN: ❌ 未设置")
        
        # 显示 MTF_SILENT_MODE
        silent = env_info['silent_mode'].lower() in ('true', '1', 'yes', 'on')
        if silent:
            if use_color:
                print(f"  MTF_SILENT_MODE: {Fore.YELLOW}{env_info['silent_mode']}{Style.RESET_ALL} {Fore.YELLOW}(全局静默模式已启用){Style.RESET_ALL}")
            else:
                print(f"  MTF_SILENT_MODE: {env_info['silent_mode']} (全局静默模式已启用)")
        else:
            if use_color:
                print(f"  MTF_SILENT_MODE: {Fore.GREEN}{env_info['silent_mode']}{Style.RESET_ALL} (消息推送已启用)")
            else:
                print(f"  MTF_SILENT_MODE: {env_info['silent_mode']} (消息推送已启用)")
        
        print(divider)
        print()

    def _env_changed(self, new_env_info: Dict[str, Any]) -> bool:
        """
        检查环境变量配置是否发生变化
        
        Args:
            new_env_info: 新的环境变量信息
            
        Returns:
            bool: 如果配置有变化返回 True，否则返回 False
        """
        if self._last_env_info is None:
            return True
        
        # 比较关键字段
        return (
            self._last_env_info['env_file'] != new_env_info['env_file'] or
            self._last_env_info['token'] != new_env_info['token'] or
            self._last_env_info['silent_mode'] != new_env_info['silent_mode']
        )

    def load_tasks(self):
        """
        从配置文件加载初始任务
        
        配置文件应为YAML格式，包含任务列表，每个任务需指定名称和命令
        任务可以包含以下参数：
        - name: 任务名称（必需）
        - command: 要执行的命令（必需）
        - status: 任务状态（可选，默认为"pending"）
        - env: 任务级环境变量（可选，字典格式）
        
        注意：status 为 "skipped" 的任务将不会被加载到任务队列中
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                task_list = yaml.safe_load(f)
                
            if not isinstance(task_list, list):
                raise ValueError("配置文件格式错误：应该是任务列表")
            
            skipped_count = 0
            for task_config in task_list:
                status = task_config.get('status', 'pending')
                
                # 跳过状态为 skipped 的任务
                if status == 'skipped':
                    skipped_count += 1
                    self.logger.info(f"跳过任务: {task_config['name']} (status: skipped)")
                    continue
                
                task = Task(
                    name=task_config['name'],
                    command=task_config['command'],
                    status=status,
                    env=task_config.get('env', {})
                )
                self.add_task(task)
            
            self.logger.info(f"已加载 {len(self.tasks)} 个任务")
            if skipped_count > 0:
                self.logger.info(f"跳过了 {skipped_count} 个任务 (status: skipped)")
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
        
        # 在任务执行前重新加载环境变量（支持运行时更新 .env 文件）
        env_info = self._load_env()
        
        # 保存原始环境变量（用于任务执行后恢复）
        original_env = {}
        
        # 如果任务有自定义环境变量
        if task.env:
            self.logger.info(f"任务使用自定义环境变量: {list(task.env.keys())}")
            
            # 保存原始值
            for key in task.env.keys():
                original_env[key] = os.environ.get(key)
            
            # 设置任务级环境变量
            for key, value in task.env.items():
                os.environ[key] = str(value)
            
            # 更新 env_info 以显示任务级配置
            env_info['token'] = os.getenv('MSG_PUSH_TOKEN')
            env_info['silent_mode'] = os.getenv('MTF_SILENT_MODE', 'false')
            env_info['task_env'] = True  # 标记为任务级配置
            
            # 显示任务级环境变量配置
            self._show_env_config(env_info)
            # 更新 last_env_info，避免下个任务误认为没变化
            self._last_env_info = env_info.copy()
        else:
            # 检查环境变量是否有变化，有变化才显示
            if self._env_changed(env_info):
                self.logger.info("检测到环境变量配置变化")
                self._show_env_config(env_info)
                self._last_env_info = env_info
        
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
            # 恢复原始环境变量
            if task.env and original_env:
                self.logger.debug("恢复原始环境变量")
                for key, value in original_env.items():
                    if value is None:
                        # 原来没有这个变量，删除它
                        os.environ.pop(key, None)
                    else:
                        # 恢复原来的值
                        os.environ[key] = value
            
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
                        status=task_config.get('status', 'pending'),
                        env=task_config.get('env', {})
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
        
        # 添加处理中断的代码
        try:
            while not self.stop_event.is_set():
                try:
                    self.check_new_tasks()
                    task = self.task_queue.get(timeout=1)
                    last_task_time = datetime.now()
                    self.execute_task(task)
                except queue.Empty:
                    # 计算已等待时间
                    wait_time = (datetime.now() - last_task_time).total_seconds()
                    
                    # 每5秒打印一次等待信息
                    if wait_time % 5 < 1:
                        remaining = 60 - wait_time
                        if remaining > 0:
                            self.logger.info(f"等待新任务中... 还有 {int(remaining)} 秒后将检查新任务")
                    
                    # 如果已标记停止，立即退出循环
                    if self.stop_event.is_set():
                        break
                        
                    if wait_time > 60:
                        self.check_new_tasks()
                        if self.task_queue.empty():
                            self.logger.info("1分钟内无新任务，准备停止任务流管理器")
                            self.stop()
                    continue
                except Exception as e:
                    self.logger.error(f"执行任务时出现异常: {str(e)}")
                    continue
        except KeyboardInterrupt:
            # 捕获键盘中断
            self.logger.info("接收到键盘中断，立即终止所有任务")
            self.stop()

        self.logger.info("任务流管理器已停止")
        self.running = False

    def stop(self):
        """
        停止任务流管理器并发送总结报告
        
        如果设置了环境变量MTF_SILENT_MODE=true，将跳过消息发送，只记录日志
        """
        self.stop_event.set()
        self.logger.info("正在停止任务流管理器...")
        
        # 等待当前任务完成
        if self.running:
            self.end_time = datetime.now()
            summary = self.generate_summary()
            self.logger.info("任务总结报告:")
            self.logger.info(summary)  # 在日志中记录摘要
            
            # 检查环境变量MTF_SILENT_MODE
            if os.getenv('MTF_SILENT_MODE', '').lower() in ('true', '1', 'yes', 'on'):
                self.logger.info(f"环境变量MTF_SILENT_MODE已设置为{os.getenv('MTF_SILENT_MODE')}，跳过发送总结报告")
                return
            
            # 发送总结报告
            self.logger.info("发送任务总结报告...")
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

def main():
    """
    任务流管理器的命令行入口点
    
    用法:
        taskflow [config_file_path]
    
    参数:
        config_file_path: 任务配置文件路径，默认为 examples/tasks.yaml
    """
    import sys
    import signal
    from threading import Thread
    
    def signal_handler(signum, frame):
        """处理终止信号 - 交互式选择是否终止运行中的任务"""
        print("\n\033[1;33m接收到终止信号 (Ctrl+C)\033[0m\n")
        
        # 1. 尝试获取manager实例
        manager_instance = None
        try:
            if 'manager' in globals():
                manager_instance = globals()['manager']
            if manager_instance is None:
                for frame_info in inspect.getouterframes(frame):
                    if 'manager' in frame_info.frame.f_locals:
                        manager_instance = frame_info.frame.f_locals['manager']
                        break
        except Exception as e:
            pass
        
        # 2. 收集运行中的任务信息
        running_tasks = []
        pending_count = 0
        completed_count = 0
        failed_count = 0
        
        if manager_instance is not None:
            try:
                for task in manager_instance.tasks:
                    if task.status == "running" and task.process:
                        running_tasks.append({
                            'name': task.name,
                            'pid': task.process.pid,
                            'start_time': task.start_time
                        })
                    elif task.status == "pending":
                        pending_count += 1
                    elif task.status == "completed":
                        completed_count += 1
                    elif task.status == "failed":
                        failed_count += 1
            except:
                pass
        
        # 3. 显示任务摘要
        print("\033[1;36m--- 任务执行摘要 ---\033[0m")
        total = len(running_tasks) + pending_count + completed_count + failed_count
        print(f"任务总数: {total}")
        print(f"已完成: \033[32m{completed_count}\033[0m | 运行中: \033[33m{len(running_tasks)}\033[0m | 等待中: {pending_count} | 失败: \033[31m{failed_count}\033[0m")
        
        # 4. 显示运行中任务的 PID
        if running_tasks:
            print(f"\n\033[1;33m⚠ 有 {len(running_tasks)} 个任务正在运行:\033[0m")
            for task in running_tasks:
                start_time = task['start_time'].strftime('%H:%M:%S') if task['start_time'] else "未知"
                print(f"  • \033[1m{task['name']}\033[0m")
                print(f"    PID: \033[1;34m{task['pid']}\033[0m  开始时间: {start_time}")
            
            print(f"\n\033[1;32m💡 这些任务进程是独立运行的，退出 taskflow 后它们会继续执行。\033[0m")
            print(f"   如需手动终止，请使用: \033[1mkill <PID>\033[0m 或 \033[1mkill -9 <PID>\033[0m\n")
        
        print("------------------------\n")
        
        # 5. 取消待执行任务
        if manager_instance is not None and pending_count > 0:
            try:
                while not manager_instance.task_queue.empty():
                    manager_instance.task_queue.get_nowait()
                for task in manager_instance.tasks:
                    if task.status == "pending":
                        task.status = "canceled"
                print(f"已取消 {pending_count} 个待执行任务")
            except:
                pass
        
        # 6. 交互式选择（只有有运行中任务时才询问）
        if running_tasks:
            print("\033[1m请选择操作:\033[0m")
            print("  [Enter/n] 退出 taskflow，保持任务继续运行 \033[2m(默认)\033[0m")
            print("  [k]       终止所有运行中的任务后退出")
            print()
            
            # 设置超时读取
            import select
            print("请在 5 秒内选择，超时将自动选择默认选项...", end=" ", flush=True)
            
            try:
                # 尝试使用 select 进行超时读取（仅 Unix 系统）
                rlist, _, _ = select.select([sys.stdin], [], [], 5)
                if rlist:
                    choice = sys.stdin.readline().strip().lower()
                else:
                    choice = ''  # 超时，使用默认
                    print()  # 换行
            except:
                # Windows 或其他不支持 select 的情况，直接使用默认
                choice = ''
            
            if choice == 'k':
                print("\n\033[1;31m正在终止所有运行中的任务...\033[0m")
                for task_info in running_tasks:
                    try:
                        pid = task_info['pid']
                        print(f"  终止任务: {task_info['name']} (PID: {pid})")
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        print(f"    进程已结束")
                    except Exception as e:
                        print(f"    终止失败: {e}")
                
                # 等待进程终止
                time.sleep(1)
                
                # 检查是否有未响应的进程
                for task_info in running_tasks:
                    try:
                        pid = task_info['pid']
                        os.kill(pid, 0)  # 检查进程是否存在
                        print(f"  \033[1;31m强制终止: {task_info['name']} (PID: {pid})\033[0m")
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # 进程已结束
                    except:
                        pass
                
                print("\n\033[32m所有任务已终止\033[0m")
            else:
                print(f"\n\033[32m保持任务继续运行，退出 taskflow...\033[0m")
        
        # 7. 尝试生成报告
        if manager_instance is not None:
            try:
                if manager_instance.is_running():
                    manager_instance.stop()
            except:
                pass
        
        print("\n\033[1mTaskflow 已退出\033[0m")
        os._exit(0)
    
    
    try:
        # 检查是否存在帮助参数或没有提供任何参数
        if len(sys.argv) <= 1 or sys.argv[1] in ['-h', '--help']:
            print_help_message()
            sys.exit(0)
        
        # 检查是否是 web 子命令
        if sys.argv[1] == 'web':
            # 启动 Web UI（不注册 CLI 信号处理器，Web UI 有自己的生命周期管理）
            run_web_server(sys.argv[2:])
            sys.exit(0)
        
        # 检查是否是 status 子命令
        if sys.argv[1] == 'status':
            show_backend_status()
            sys.exit(0)
        
        # 检查是否是 monitor 子命令
        if sys.argv[1] == 'monitor':
            run_pid_monitor(sys.argv[2:])
            sys.exit(0)
            
        # 有参数但不是帮助参数，视为配置文件路径
        config_path = sys.argv[1]
            
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            print(f"\033[1;31m错误：配置文件 '{config_path}' 不存在！\033[0m")
            print_help_message()
            sys.exit(1)
        
        # 【仅 CLI 模式】注册信号处理器
        # Web 模式有自己的生命周期管理，不需要这个处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 创建并启动任务流管理器
        manager = TaskFlow(config_path)
        manager_thread = Thread(target=manager.run)
        manager_thread.start()
        manager_thread.join()
    except Exception as e:
        print(f"任务流管理器运行出错: {str(e)}")
        if 'manager' in globals() and manager.is_running():
            manager.stop()
    finally:
        if 'manager' in globals() and manager.is_running():
            manager.stop()
            if 'manager_thread' in locals() and manager_thread.is_alive():
                manager_thread.join()



def run_web_server(args: list):
    """
    启动 Web UI 服务器
    
    Args:
        args: 命令行参数列表
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='taskflow web',
        description='启动 MultiTaskFlow Web UI'
    )
    parser.add_argument('config', nargs='?', help='任务配置文件路径（可选）')
    parser.add_argument('--workspace', '-w', help='工作空间目录')
    parser.add_argument('--host', default='0.0.0.0', help='服务器地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', '-p', type=int, default=8080, help='服务器端口 (默认: 8080)')
    parser.add_argument('--reload', '-r', action='store_true', help='启用热重载（开发模式）')
    
    parsed = parser.parse_args(args)
    
    # 检查是否安装了 web 依赖
    try:
        from .web.server import run_server
    except ImportError as e:
        print("\033[1;31m错误：未安装 Web UI 依赖！\033[0m")
        print("请运行以下命令安装：")
        print("  pip install multitaskflow[web]")
        print(f"\n详细错误: {e}")
        sys.exit(1)
    
    # 确定工作空间
    workspace = parsed.workspace
    config = parsed.config
    
    if not config and not workspace:
        # 无参数时使用当前目录
        workspace = str(os.getcwd())
    
    # 启动服务
    run_server(
        config_path=config,
        workspace_dir=workspace,
        host=parsed.host,
        port=parsed.port,
        reload=parsed.reload
    )


def show_backend_status():
    """
    显示运行中的 MultiTaskFlow 后端服务状态
    
    扫描系统进程，查找运行中的 uvicorn/fastapi 进程，
    显示其 PID、端口、工作区等信息。
    """
    print("\n\033[1;36m=== MultiTaskFlow 后端状态 ===\033[0m\n")
    
    backends = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'create_time']):
        try:
            cmdline = proc.info['cmdline'] or []
            cmdline_str = " ".join(cmdline)
            
            # 查找 uvicorn 运行 multitaskflow 的进程
            if 'uvicorn' in cmdline_str.lower() and 'multitaskflow' in cmdline_str.lower():
                # 提取端口号
                port = 8080  # 默认端口
                for i, arg in enumerate(cmdline):
                    if arg == '--port' and i + 1 < len(cmdline):
                        try:
                            port = int(cmdline[i + 1])
                        except ValueError:
                            pass
                    elif arg.startswith('--port='):
                        try:
                            port = int(arg.split('=')[1])
                        except ValueError:
                            pass
                
                # 获取工作目录
                cwd = proc.info.get('cwd', '未知')
                
                # 计算运行时长
                create_time = datetime.fromtimestamp(proc.info['create_time'])
                uptime = datetime.now() - create_time
                hours, remainder = divmod(int(uptime.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{hours}h{minutes}m" if hours > 0 else f"{minutes}m{seconds}s"
                
                backends.append({
                    'pid': proc.info['pid'],
                    'port': port,
                    'cwd': cwd,
                    'uptime': uptime_str
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if backends:
        print(f"\033[1;32m发现 {len(backends)} 个运行中的后端:\033[0m\n")
        for i, b in enumerate(backends, 1):
            print(f"  [{i}] PID: \033[1;33m{b['pid']}\033[0m")
            print(f"      端口: \033[1;34mhttp://localhost:{b['port']}\033[0m")
            print(f"      工作区: {b['cwd']}")
            print(f"      运行时长: {b['uptime']}")
            print()
    else:
        print("\033[1;33m未发现运行中的 MultiTaskFlow 后端\033[0m")
        print("\n启动后端:")
        print("  taskflow web                    # 使用当前目录")
        print("  taskflow web -w /path/to/dir    # 指定工作区")
        print("  taskflow web --port 9000        # 指定端口")
    
    print()


def run_pid_monitor(args: list):
    """
    临时监控指定 PID，进程结束后发送通知
    
    Args:
        args: 命令行参数列表
    """
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        prog='taskflow monitor',
        description='监控指定 PID，进程结束后发送通知'
    )
    parser.add_argument('pid', type=int, help='要监控的进程 PID')
    parser.add_argument('--name', '-n', default=None, help='进程名称（用于通知），默认从进程命令获取')
    parser.add_argument('--silent', '-s', action='store_true', help='静默模式，不发送通知')
    
    parsed = parser.parse_args(args)
    
    # 验证 PID 存在
    try:
        proc = psutil.Process(parsed.pid)
        cmdline = proc.cmdline()
        proc_name = parsed.name or (cmdline[0] if cmdline else f"PID {parsed.pid}")
        
        # 简化进程名称显示
        if len(proc_name) > 50:
            proc_name = "..." + proc_name[-47:]
        
    except psutil.NoSuchProcess:
        print(f"\033[1;31m错误: PID {parsed.pid} 不存在\033[0m")
        sys.exit(1)
    except psutil.AccessDenied:
        print(f"\033[1;31m错误: 无权限访问 PID {parsed.pid}\033[0m")
        sys.exit(1)
    
    print(f"\n\033[1;36m=== 开始监控进程 ===\033[0m")
    print(f"  PID: \033[1;33m{parsed.pid}\033[0m")
    print(f"  名称: {proc_name}")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n\033[1;34m正在监控中，按 Ctrl+C 退出...\033[0m\n")
    
    start_time = datetime.now()
    
    try:
        # 监控循环
        while True:
            try:
                if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    break
                time.sleep(5)
            except psutil.NoSuchProcess:
                break
    except KeyboardInterrupt:
        print("\n\033[1;33m用户中断监控\033[0m")
        sys.exit(0)
    
    # 进程结束
    end_time = datetime.now()
    duration = end_time - start_time
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        duration_str = f"{hours}小时{minutes}分{seconds}秒"
    elif minutes > 0:
        duration_str = f"{minutes}分{seconds}秒"
    else:
        duration_str = f"{seconds}秒"
    
    print(f"\n\033[1;32m=== 进程已结束 ===\033[0m")
    print(f"  PID: {parsed.pid}")
    print(f"  运行时长: {duration_str}")
    print(f"  结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 发送通知
    if not parsed.silent:
        print(f"\n\033[1;34m正在发送通知...\033[0m")
        
        content = f"""
【进程监控完成】

进程名称: {proc_name}
PID: {parsed.pid}
运行时长: {duration_str}
结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}

---
由 taskflow monitor 发送
        """
        
        success = Msg_push(
            title=f"进程结束: {parsed.name or f'PID {parsed.pid}'}",
            content=content
        )
        
        if success:
            print("\033[1;32m✓ 通知已发送\033[0m")
        else:
            print("\033[1;31m✗ 通知发送失败，请检查 MSG_PUSH_TOKEN 配置\033[0m")
    
    print()


def print_help_message():
    """打印帮助信息"""
    print("\n\033[1;36m=== MultiTaskFlow 使用帮助 ===\033[0m")
    print("\033[1m用法:\033[0m")
    print("  taskflow <配置文件路径>           # CLI 模式：顺序执行任务")
    print("  taskflow web [选项]               # Web 模式：启动可视化管理界面")
    print("  taskflow status                   # 查看运行中的后端服务状态")
    print("  taskflow monitor <pid> [选项]     # 监控指定 PID，结束后发送通知")
    print("\n\033[1m参数:\033[0m")
    print("  <配置文件路径>  YAML格式的任务配置文件路径")
    print("  -h, --help     显示此帮助信息并退出")
    
    print("\n\033[1;33m=== Web UI 子命令 ===\033[0m")
    print("\033[1m用法:\033[0m taskflow web [配置文件] [选项]")
    print("\n\033[1mWeb 选项:\033[0m")
    print("  [配置文件]         可选，任务配置文件路径")
    print("  -w, --workspace    工作空间目录")
    print("  -p, --port PORT    服务器端口 (默认: 8080)")
    print("  --host HOST        服务器地址 (默认: 0.0.0.0)")
    print("  -r, --reload       启用热重载（开发模式）")
    
    print("\n\033[1mWeb UI 示例:\033[0m")
    print("  # 使用当前目录作为工作空间")
    print("  taskflow web")
    print("")
    print("  # 加载指定 YAML 文件")
    print("  taskflow web tasks.yaml")
    print("")
    print("  # 指定端口")
    print("  taskflow web --port 9000")
    print("")
    print("  # 指定工作空间目录")
    print("  taskflow web -w /path/to/workspace")
    
    print("\n\033[1;33m=== CLI 模式 ===\033[0m")
    print("\033[1m命令行使用示例:\033[0m")
    print("  # 使用配置文件启动任务流")
    print("  taskflow tasks.yaml")
    print("")
    print("  # 后台运行并记录日志")
    print("  nohup taskflow my_tasks.yaml > taskflow.log 2>&1 &")
    
    print("\n\033[1;33m=== 状态查看 ===\033[0m")
    print("\033[1m用法:\033[0m taskflow status")
    print("  显示所有运行中的 MultiTaskFlow 后端服务")
    print("  包括 PID、端口、工作区、运行时长")
    
    print("\n\033[1;33m=== 进程监控 ===\033[0m")
    print("\033[1m用法:\033[0m taskflow monitor <pid> [选项]")
    print("\n\033[1m监控选项:\033[0m")
    print("  <pid>              要监控的进程 ID（必需）")
    print("  -n, --name NAME    进程名称（用于通知）")
    print("  -s, --silent       静默模式，不发送通知")
    print("\n\033[1m监控示例:\033[0m")
    print("  # 监控 PID 12345")
    print("  taskflow monitor 12345")
    print("")
    print("  # 指定名称")
    print("  taskflow monitor 12345 --name '训练任务'")
    print("")
    print("  # 静默模式（只打印，不发通知）")
    print("  taskflow monitor 12345 --silent")
    
    print("\n\033[1m配置文件格式示例:\033[0m")
    print("""# 任务流配置示例
# 每个任务包含名称和要执行的命令
# 任务将按照列表顺序依次执行

- name: "示例任务1"
  command: "python example1.py"
  status: "pending"

- name: "示例任务2" 
  command: "python example2.py"
  status: "pending"
""")
    
    print("\n\033[1m环境变量配置:\033[0m")
    print("  可在当前目录创建 .env 文件，配置以下环境变量:")
    print("  MSG_PUSH_TOKEN  - 消息推送令牌 (用于任务完成通知)")
    
    print("\n\033[1m安装 Web UI 依赖:\033[0m")
    print("  pip install multitaskflow[web]")
    
    print("\n\033[1m更多信息:\033[0m")
    print("请访问 GitHub 项目页面查看详细文档：")
    print("\033[1;34mhttps://github.com/Polaris-F/MultiTaskFlow\033[0m\n")

if __name__ == "__main__":
    """
    任务流管理器的使用示例
    """
    main() 
