#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务管理器

负责管理任务队列、执行状态和历史记录。
与现有 TaskFlow 类分离，专注于 Web UI 场景。
"""

import os
import re
import subprocess
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import yaml


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    command: str
    status: TaskStatus = TaskStatus.PENDING
    gpu: Optional[List[int]] = None
    note: Optional[str] = None  # 备注信息
    
    # 运行时信息
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    process: Optional[subprocess.Popen] = field(default=None, repr=False)
    log_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 响应）"""
        result = {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "status": self.status.value,
            "gpu": self.gpu,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.get_duration(),
            "error_message": self.error_message,
            "log_file": self.log_file,
            "note": self.note,
        }
        return result
    
    def get_duration(self) -> Optional[float]:
        """获取运行时长（秒）"""
        if not self.start_time:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


def parse_gpu_from_command(command: str) -> Optional[List[int]]:
    """
    从 command 中解析 CUDA_VISIBLE_DEVICES
    
    Examples:
        "CUDA_VISIBLE_DEVICES=0,1 python train.py" → [0, 1]
        "CUDA_VISIBLE_DEVICES=2 python train.py"   → [2]
        "python train.py"                          → None
    """
    match = re.search(r'CUDA_VISIBLE_DEVICES=([0-9,]+)', command)
    if match:
        return [int(x.strip()) for x in match.group(1).split(',')]
    return None


class TaskManager:
    """
    任务管理器
    
    负责：
    - 从 YAML 加载任务
    - 管理任务队列（增删改查）
    - 执行任务（手动触发）
    - GPU 冲突检测
    - 维护执行历史
    """
    
    def __init__(self, config_path: str, history_file: str = None):
        """
        初始化任务管理器
        
        Args:
            config_path: 任务配置文件路径
            history_file: 历史记录文件路径（可选）
        """
        self.config_path = Path(config_path).resolve()  # 确保使用绝对路径
        self.config_dir = self.config_path.parent
        
        # 任务存储
        self.tasks: Dict[str, Task] = {}  # id -> Task
        self.task_order: List[str] = []   # 任务顺序（id列表）
        
        # 计数器（用于生成任务ID）
        self._task_counter = 0
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 队列自动执行状态
        self.queue_running = False
        self._queue_thread = None
        self._queue_stop_flag = False
        
        # 日志目录
        self.log_dir = self.config_dir / "logs" / "tasks"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 主进程日志文件（包含 YAML 文件名以区分不同队列）
        from datetime import datetime as dt
        yaml_name = self.config_path.stem  # 获取 YAML 文件名（不含扩展名）
        main_log_name = f"webui_{yaml_name}_{dt.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.main_log_file = str(self.config_dir / "logs" / main_log_name)
        
        # 历史记录管理器
        if history_file is None:
            history_file = str(self.config_dir / "logs" / ".history.json")
        from .history import HistoryManager
        self.history_manager = HistoryManager(history_file)
        
        # 设置日志（使用唯一的 logger 名称，避免多队列日志混淆）
        # 使用配置文件路径的哈希作为唯一标识
        import hashlib
        logger_id = hashlib.md5(str(self.config_path).encode()).hexdigest()[:8]
        self.logger = logging.getLogger(f"TaskManager_{logger_id}")
        self.logger.setLevel(logging.INFO)
        
        # 清除现有处理器（防止重复添加）
        self.logger.handlers.clear()
        
        # 添加文件处理器
        file_handler = logging.FileHandler(self.main_log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def _generate_task_id(self) -> str:
        """生成任务ID - 使用 UUID 确保全局唯一性"""
        import uuid
        self._task_counter += 1
        # 格式: task_{counter}_{uuid前8位} 确保唯一且可读
        return f"task_{self._task_counter:04d}_{uuid.uuid4().hex[:8]}"
    
    def load_tasks(self) -> int:
        """
        从配置文件加载任务
        
        Returns:
            加载的任务数量
        """
        if not self.config_path.exists():
            self.logger.warning(f"配置文件不存在: {self.config_path}")
            return 0
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                task_list = yaml.safe_load(f)
            
            if not isinstance(task_list, list):
                self.logger.error("配置文件格式错误：应该是任务列表")
                return 0
            
            count = 0
            for task_config in task_list:
                status = task_config.get('status', 'pending')
                
                # 跳过已标记为 skipped 的任务
                if status == 'skipped':
                    continue
                
                task_id = self._generate_task_id()
                command = task_config['command']
                
                task = Task(
                    id=task_id,
                    name=task_config['name'],
                    command=command,
                    status=TaskStatus.PENDING,
                    gpu=parse_gpu_from_command(command)
                )
                
                self.tasks[task_id] = task
                self.task_order.append(task_id)
                count += 1
            
            self.logger.info(f"已加载 {count} 个任务")
            
            # 保存已加载的任务名称用于去重
            self._loaded_task_names = {t.name for t in self.tasks.values()}
            
            return count
            
        except Exception as e:
            self.logger.error(f"加载任务失败: {e}")
            return 0
    
    def check_yaml_updates(self) -> Dict[str, Any]:
        """
        检查 YAML 文件是否有新任务
        
        对比当前已加载的任务，找出新增的任务并校验格式。
        
        Returns:
            {
                "new_tasks": [{"name": ..., "command": ..., "valid": True/False, "error": ...}],
                "total_in_yaml": 总任务数,
                "loaded_count": 成功加载数
            }
        """
        result = {
            "new_tasks": [],
            "total_in_yaml": 0,
            "loaded_count": 0,
            "error": None
        }
        
        if not self.config_path.exists():
            result["error"] = "配置文件不存在"
            return result
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                task_list = yaml.safe_load(f)
            
            if not isinstance(task_list, list):
                result["error"] = "配置文件格式错误：应该是任务列表"
                return result
            
            result["total_in_yaml"] = len(task_list)
            
            # 获取当前已有的任务名称
            existing_names = {t.name for t in self.tasks.values()}
            existing_names.update(getattr(self, '_loaded_task_names', set()))
            
            new_tasks = []
            for task_config in task_list:
                # 跳过 skipped 状态
                if task_config.get('status') == 'skipped':
                    continue
                
                name = task_config.get('name', '')
                command = task_config.get('command', '')
                
                # 检查是否是新任务
                if name in existing_names:
                    continue
                
                # 校验格式
                task_info = {
                    "name": name,
                    "command": command,
                    "valid": True,
                    "error": None
                }
                
                if not name:
                    task_info["valid"] = False
                    task_info["error"] = "缺少任务名称"
                elif not command:
                    task_info["valid"] = False
                    task_info["error"] = "缺少执行命令"
                
                new_tasks.append(task_info)
            
            result["new_tasks"] = new_tasks
            return result
            
        except yaml.YAMLError as e:
            result["error"] = f"YAML 解析错误: {str(e)}"
            return result
        except Exception as e:
            result["error"] = f"检查失败: {str(e)}"
            return result
    
    def load_new_tasks_from_yaml(self) -> Dict[str, Any]:
        """
        从 YAML 加载新任务（只加载格式正确的新任务）
        
        Returns:
            {"loaded": 加载数量, "skipped": 跳过数量, "errors": 错误列表}
        """
        check_result = self.check_yaml_updates()
        
        if check_result["error"]:
            return {"loaded": 0, "skipped": 0, "errors": [check_result["error"]]}
        
        loaded = 0
        skipped = 0
        errors = []
        
        for task_info in check_result["new_tasks"]:
            if not task_info["valid"]:
                errors.append(f"{task_info['name']}: {task_info['error']}")
                skipped += 1
                continue
            
            # 添加到队列
            with self._lock:
                task_id = self._generate_task_id()
                task = Task(
                    id=task_id,
                    name=task_info["name"],
                    command=task_info["command"],
                    status=TaskStatus.PENDING,
                    gpu=parse_gpu_from_command(task_info["command"])
                )
                self.tasks[task_id] = task
                self.task_order.append(task_id)
                
                # 更新已加载名称集合
                if not hasattr(self, '_loaded_task_names'):
                    self._loaded_task_names = set()
                self._loaded_task_names.add(task_info["name"])
                
                loaded += 1
                self.logger.info(f"加载新任务: {task_info['name']} (ID: {task_id})")
        
        return {"loaded": loaded, "skipped": skipped, "errors": errors}
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务（按顺序）"""
        return [self.tasks[tid] for tid in self.task_order if tid in self.tasks]
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待执行任务"""
        return [t for t in self.get_all_tasks() if t.status == TaskStatus.PENDING]
    
    def get_running_tasks(self) -> List[Task]:
        """获取运行中任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取指定任务"""
        return self.tasks.get(task_id)
    
    def add_task(self, name: str, command: str, note: str = None) -> Task:
        """
        添加新任务
        
        Args:
            name: 任务名称
            command: 执行命令
            note: 备注信息
        
        Returns:
            新创建的任务
        """
        with self._lock:
            task_id = self._generate_task_id()
            task = Task(
                id=task_id,
                name=name,
                command=command,
                status=TaskStatus.PENDING,
                gpu=parse_gpu_from_command(command),
                note=note
            )
            self.tasks[task_id] = task
            self.task_order.append(task_id)
            self.logger.info(f"添加任务: {name} (ID: {task_id})")
            return task
    
    def update_task(self, task_id: str, name: str = None, command: str = None, note: str = None) -> Optional[Task]:
        """
        更新任务
        
        Args:
            task_id: 任务ID
            name: 新名称
            command: 新命令
            note: 新备注
        
        Returns:
            更新后的任务，如果不存在返回 None
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if task.status == TaskStatus.RUNNING:
            raise ValueError("无法修改运行中的任务")
        
        with self._lock:
            if name is not None:
                task.name = name
            if command is not None:
                task.command = command
                task.gpu = parse_gpu_from_command(command)
            if note is not None:
                task.note = note
            
            self.logger.info(f"更新任务: {task.name} (ID: {task_id})")
            return task
    
    def update_note(self, task_id: str, note: str) -> bool:
        """
        更新任务备注（允许运行中和已完成任务）
        
        TODO: 需要添加对应的 API 端点和前端 UI
        
        Args:
            task_id: 任务ID
            note: 新备注
        
        Returns:
            是否成功更新
        """
        # 先在活动任务中查找
        task = self.tasks.get(task_id)
        if task:
            with self._lock:
                task.note = note
                self.logger.info(f"更新任务备注: {task.name} (ID: {task_id})")
                return True
        
        # 在历史记录中查找并更新
        return self.history_manager.update_note(task_id, note)
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功删除
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.RUNNING:
            raise ValueError("无法删除运行中的任务")
        
        with self._lock:
            del self.tasks[task_id]
            self.task_order.remove(task_id)
            self.logger.info(f"删除任务: {task.name} (ID: {task_id})")
            return True
    
    def reorder_tasks(self, new_order: List[str]) -> bool:
        """
        重新排序任务
        
        Args:
            new_order: 新的任务ID顺序
        
        Returns:
            是否成功
        """
        # 验证：只能重排待执行任务
        pending_ids = [t.id for t in self.get_pending_tasks()]
        
        # 检查新顺序是否有效
        if set(new_order) != set(pending_ids):
            return False
        
        with self._lock:
            # 保留运行中任务的位置，重排待执行任务
            running_ids = [t.id for t in self.get_running_tasks()]
            self.task_order = running_ids + new_order
            return True
    
    def get_busy_gpus(self) -> set:
        """获取当前被占用的 GPU"""
        busy = set()
        for task in self.get_running_tasks():
            if task.gpu:
                busy.update(task.gpu)
        return busy
    
    def check_gpu_conflict(self, task_id: str) -> Optional[str]:
        """
        检查 GPU 冲突
        
        Args:
            task_id: 要检查的任务ID
        
        Returns:
            冲突描述，无冲突返回 None
        """
        task = self.tasks.get(task_id)
        if not task or not task.gpu:
            return None
        
        busy_gpus = self.get_busy_gpus()
        conflict = set(task.gpu) & busy_gpus
        
        if conflict:
            # 找到占用这些 GPU 的任务
            for running_task in self.get_running_tasks():
                if running_task.gpu and set(running_task.gpu) & conflict:
                    return f"GPU {','.join(map(str, conflict))} 正被「{running_task.name}」占用"
        
        return None
    
    def run_task(self, task_id: str) -> Task:
        """
        运行指定任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务实例
        
        Raises:
            ValueError: 任务不存在、状态无效或 GPU 冲突
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task.status != TaskStatus.PENDING:
            raise ValueError(f"任务状态无效: {task.status}")
        
        # 检查 GPU 冲突
        conflict = self.check_gpu_conflict(task_id)
        if conflict:
            raise ValueError(conflict)
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\-]', '_', task.name)[:30]
        log_filename = f"{task.id}_{safe_name}_{timestamp}.log"
        task.log_file = str(self.log_dir / log_filename)
        
        # 启动进程
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.start_time = datetime.now()
            
            log_file = open(task.log_file, 'w', encoding='utf-8')
            
            # 设置环境变量确保 Python 子进程使用 UTF-8 和无缓冲输出
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUNBUFFERED'] = '1'  # 禁用输出缓冲，实时显示日志
            
            task.process = subprocess.Popen(
                task.command,
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(self.config_dir),
                text=True,
                encoding='utf-8',
                env=env
            )
            
            # 从待执行列表移除
            if task_id in self.task_order:
                self.task_order.remove(task_id)
        
        # 启动监控线程
        monitor_thread = threading.Thread(
            target=self._monitor_task,
            args=(task,),
            daemon=True
        )
        monitor_thread.start()
        
        self.logger.info(f"启动任务: {task.name} (PID: {task.process.pid})")
        return task
    
    def _monitor_task(self, task: Task):
        """监控任务执行状态"""
        if not task.process:
            return
        
        return_code = task.process.wait()
        task.end_time = datetime.now()
        
        if return_code == 0:
            task.status = TaskStatus.COMPLETED
            self.logger.info(f"任务完成: {task.name}")
        else:
            task.status = TaskStatus.FAILED
            task.error_message = f"退出码: {return_code}"
            self.logger.error(f"任务失败: {task.name} ({task.error_message})")
        
        # 添加到历史（持久化）
        self.history_manager.add(task.to_dict())
        
        # 从任务列表移除
        with self._lock:
            if task.id in self.tasks:
                del self.tasks[task.id]
    
    def stop_task(self, task_id: str) -> bool:
        """
        停止指定任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功停止
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        if task.process:
            task.process.terminate()
            try:
                task.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                task.process.kill()
            
            task.status = TaskStatus.STOPPED
            task.end_time = datetime.now()
            self.logger.info(f"停止任务: {task.name}")
            
            # 添加到历史（持久化）
            self.history_manager.add(task.to_dict())
            
            # 从任务列表移除
            with self._lock:
                if task.id in self.tasks:
                    del self.tasks[task.id]
            
            return True
        
        return False
    
    def stop_all(self):
        """停止所有运行中的任务"""
        for task in list(self.get_running_tasks()):
            self.stop_task(task.id)
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        Args:
            limit: 最大返回数量
        
        Returns:
            历史任务列表（最新在前）
        """
        return self.history_manager.get_all(limit)
    
    def clear_history(self):
        """清空执行历史"""
        self.history_manager.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态摘要"""
        return {
            "pending_count": len(self.get_pending_tasks()),
            "running_count": len(self.get_running_tasks()),
            "history_count": self.history_manager.count(),
            "busy_gpus": list(self.get_busy_gpus()),
            "config_path": str(self.config_path),
            "queue_running": self.queue_running,
        }
    
    def start_queue(self):
        """开始队列自动执行"""
        if self.queue_running:
            return
        
        self.queue_running = True
        self._queue_stop_flag = False
        self._queue_thread = threading.Thread(target=self._run_queue, daemon=True)
        self._queue_thread.start()
        self.logger.info("队列自动执行已启动")
    
    def stop_queue(self):
        """停止队列自动执行（完成当前任务后停止）"""
        self._queue_stop_flag = True
        self.logger.info("队列将在当前任务完成后停止")
    
    def _run_queue(self):
        """队列执行线程"""
        import time
        
        try:
            while not self._queue_stop_flag:
                # 等待当前任务完成
                while self.get_running_tasks():
                    if self._queue_stop_flag:
                        break
                    time.sleep(1)
                
                if self._queue_stop_flag:
                    break
                
                # 获取下一个待执行任务
                pending = self.get_pending_tasks()
                if not pending:
                    self.logger.info("队列已完成：没有更多待执行任务")
                    break
                
                next_task = pending[0]
                
                # 检查 GPU 冲突
                conflict = self.check_gpu_conflict(next_task.id)
                if conflict:
                    self.logger.warning(f"等待 GPU: {conflict}")
                    time.sleep(5)
                    continue
                
                # 运行任务
                try:
                    self.run_task(next_task.id)
                    self.logger.info(f"队列启动任务: {next_task.name}")
                except Exception as e:
                    self.logger.error(f"队列执行失败: {e}")
                    break
                
                # 等待一小段时间再检查下一个
                time.sleep(2)
        
        finally:
            self.queue_running = False
            self._queue_stop_flag = False
            self.logger.info("队列自动执行已停止")

