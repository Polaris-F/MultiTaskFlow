#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
队列管理器

管理多个独立的任务队列，每个队列对应一个 YAML 配置文件。
支持跨队列 GPU 冲突检测。
支持任务进程独立：WebUI 重启不影响运行中的任务。
"""

import json
import uuid
import logging
import threading
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from .manager import TaskManager, Task, TaskStatus

logger = logging.getLogger("QueueManager")


class QueueManager:
    """
    队列管理器
    
    管理多个 TaskManager（现在称为 TaskQueue），每个对应一个 YAML 文件。
    提供跨队列 GPU 冲突检测和统一的队列管理接口。
    支持任务进程持久化：WebUI 重启后可恢复监控运行中的任务。
    """
    
    def __init__(self, workspace_dir: str = None):
        """
        初始化队列管理器
        
        Args:
            workspace_dir: 工作空间目录，存放 .workspace.json
        """
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        self.workspace_file = self.workspace_dir / ".workspace.json"
        self.queues: Dict[str, TaskManager] = {}
        self.queue_configs: Dict[str, Dict[str, Any]] = {}
        
        # 运行中任务的 PID 持久化
        self.running_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # 确保工作空间目录存在
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载工作空间配置（包括恢复运行中任务）
        self._load_workspace()
        
        logger.info(f"队列管理器初始化完成，工作空间: {self.workspace_dir}")
    
    def _load_workspace(self):
        """从 .workspace.json 加载队列配置和运行中任务"""
        if not self.workspace_file.exists():
            logger.info("工作空间配置文件不存在，创建新配置")
            self._save_workspace()
            return
        
        try:
            with open(self.workspace_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载运行中任务状态
            self.running_tasks = data.get('running_tasks', {})
            
            for queue_config in data.get('queues', []):
                queue_id = queue_config.get('id')
                yaml_path = queue_config.get('yaml_path')
                
                if queue_id and yaml_path and Path(yaml_path).exists():
                    try:
                        self._load_queue(queue_id, queue_config)
                        logger.info(f"加载队列: {queue_config.get('name')} ({yaml_path})")
                    except Exception as e:
                        logger.error(f"加载队列失败 {yaml_path}: {e}")
                else:
                    logger.warning(f"跳过无效队列配置: {queue_config}")
            
            # 恢复运行中任务的监控
            self._restore_running_tasks()
            
            # 恢复之前正在运行的队列
            for queue_config in data.get('queues', []):
                queue_id = queue_config.get('id')
                was_running = queue_config.get('queue_running', False)
                
                if queue_id in self.queues and was_running:
                    queue = self.queues[queue_id]
                    # 只有有待处理任务时才自动启动队列
                    if queue.get_pending_tasks():
                        try:
                            queue.start_queue()
                            logger.info(f"队列已自动恢复运行: {queue_config.get('name')}")
                        except Exception as e:
                            logger.error(f"恢复队列运行失败: {e}")
                    
        except Exception as e:
            logger.error(f"加载工作空间配置失败: {e}")
    
    def _load_queue(self, queue_id: str, config: Dict[str, Any]):
        """加载单个队列"""
        yaml_path = config['yaml_path']
        # 历史文件在 YAML 所在目录的 logs/.history.json
        yaml_dir = Path(yaml_path).parent
        history_file = yaml_dir / "logs" / ".history.json"
        
        # 创建回调函数（闭包捕获 queue_id）
        def on_task_started(task_id, pid, log_file, task_name, command):
            self._on_task_started(queue_id, task_id, pid, log_file, task_name, command)
        
        def on_task_finished(task_id):
            self._on_task_finished(task_id)
        
        manager = TaskManager(
            yaml_path, 
            str(history_file),
            on_task_started=on_task_started,
            on_task_finished=on_task_finished
        )
        self.queues[queue_id] = manager
        self.queue_configs[queue_id] = config
    
    def _save_workspace(self):
        """保存工作空间配置到 .workspace.json（包括运行中任务和队列状态）"""
        # 更新队列配置中的运行状态
        for queue_id, config in self.queue_configs.items():
            if queue_id in self.queues:
                config['queue_running'] = self.queues[queue_id].queue_running
        
        data = {
            "version": "1.1",
            "updated_at": datetime.now().isoformat(),
            "queues": list(self.queue_configs.values()),
            "running_tasks": self.running_tasks
        }
        
        try:
            with open(self.workspace_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存工作空间配置失败: {e}")
    
    def _on_task_started(self, queue_id: str, task_id: str, pid: int, log_file: str, task_name: str, command: str):
        """任务启动回调：持久化 PID 和命令"""
        with self._lock:
            self.running_tasks[task_id] = {
                "queue_id": queue_id,
                "pid": pid,
                "log_file": log_file,
                "task_name": task_name,
                "command": command,
                "start_time": datetime.now().isoformat()
            }
            self._save_workspace()
        logger.info(f"任务 PID 已持久化: {task_name} (PID: {pid})")
    
    def _on_task_finished(self, task_id: str):
        """任务完成回调：从持久化存储中移除 PID"""
        with self._lock:
            if task_id in self.running_tasks:
                task_name = self.running_tasks[task_id].get('task_name', task_id)
                del self.running_tasks[task_id]
                self._save_workspace()
                logger.info(f"任务 PID 已移除: {task_name}")
    
    def _restore_running_tasks(self):
        """恢复运行中任务的监控"""
        if not self.running_tasks:
            return
        
        tasks_to_remove = []
        
        for task_id, task_info in self.running_tasks.items():
            pid = task_info.get('pid')
            queue_id = task_info.get('queue_id')
            log_file = task_info.get('log_file')
            task_name = task_info.get('task_name', task_id)
            command = task_info.get('command', '(命令未保存)')
            
            # 检查进程是否仍在运行
            if pid and self._is_process_running(pid):
                logger.info(f"恢复任务监控: {task_name} (PID: {pid})")
                
                # 在对应队列中恢复任务
                queue = self.queues.get(queue_id)
                if queue:
                    self._restore_task_in_queue(queue, task_id, pid, log_file, task_name, command)
            else:
                logger.info(f"任务已完成或进程不存在: {task_name} (PID: {pid})")
                tasks_to_remove.append(task_id)
        
        # 移除已完成的任务
        for task_id in tasks_to_remove:
            del self.running_tasks[task_id]
        
        if tasks_to_remove:
            self._save_workspace()
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否仍在运行"""
        try:
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _restore_task_in_queue(self, queue: TaskManager, task_id: str, pid: int, log_file: str, task_name: str, command: str):
        """在队列中恢复任务"""
        import subprocess
        
        # 创建任务对象，使用原始命令
        task = Task(
            id=task_id,
            name=task_name,
            command=command,
            status=TaskStatus.RUNNING,
            log_file=log_file,
            note="(WebUI 重启后恢复的任务)"
        )
        task.start_time = datetime.now()
        
        # 创建一个假的 process 对象用于监控
        # 我们直接通过 PID 监控进程状态
        task.process = None  # 不需要实际的 Popen 对象
        
        # 将任务添加到队列
        queue.tasks[task_id] = task
        
        # 启动 PID 监控线程
        monitor_thread = threading.Thread(
            target=self._monitor_pid,
            args=(queue, task, pid),
            daemon=True
        )
        monitor_thread.start()
    
    # ============ 日志分析配置 ============
    
    # 成功标记 - 日志中出现这些字符串表示任务成功
    SUCCESS_MARKERS = [
        "Results saved to",           # YOLO 训练完成
        "[MTF:SUCCESS]",              # MultiTaskFlow 自定义成功标记
        "Training complete",          # 通用训练完成
        "训练完成",                    # 中文训练完成
        "Successfully completed",     # 通用成功
    ]
    
    # 失败标记 - 日志中出现这些字符串表示任务失败
    FAILURE_MARKERS = [
        "[MTF:FAILED]",               # MultiTaskFlow 自定义失败标记
        "CUDA out of memory",         # GPU 内存不足
        "RuntimeError:",              # Python 运行时错误
        "OutOfMemoryError",           # 内存不足
        "Traceback (most recent",     # Python 异常追踪
    ]
    
    def _check_log_for_status(self, log_file: str) -> Optional[bool]:
        """
        检查日志文件判断任务状态
        
        Returns:
            True: 成功（找到成功标记）
            False: 失败（找到失败标记）
            None: 无法确定
        """
        if not log_file:
            return None
        
        log_path = Path(log_file)
        if not log_path.exists():
            return None
        
        try:
            # 只读取最后 100KB 的日志（避免读取过大的文件）
            file_size = log_path.stat().st_size
            read_size = min(file_size, 100 * 1024)
            
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                if file_size > read_size:
                    f.seek(file_size - read_size)
                content = f.read()
            
            # 先检查失败标记（失败优先）
            for marker in self.FAILURE_MARKERS:
                if marker in content:
                    logger.debug(f"日志中发现失败标记: {marker}")
                    return False
            
            # 再检查成功标记
            for marker in self.SUCCESS_MARKERS:
                if marker in content:
                    logger.debug(f"日志中发现成功标记: {marker}")
                    return True
            
            return None
        except Exception as e:
            logger.warning(f"读取日志文件失败: {e}")
            return None
    
    def _monitor_pid(self, queue: TaskManager, task: Task, pid: int):
        """通过 PID 监控进程状态，结合日志分析判断任务结果"""
        import time
        
        return_code = None
        process_ended = False
        
        try:
            process = psutil.Process(pid)
            # 等待进程结束
            while process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                time.sleep(1)
            
            process_ended = True
            # 进程已结束，尝试获取返回码
            try:
                return_code = process.wait(timeout=0)
            except psutil.TimeoutExpired:
                pass
                    
        except psutil.NoSuchProcess:
            # 进程不存在了
            process_ended = True
            return_code = None
        except psutil.AccessDenied:
            # 无权限访问进程
            process_ended = True
            return_code = -1
        except Exception as e:
            queue.logger.warning(f"监控进程 {pid} 时出错: {e}")
            process_ended = True
            return_code = -1
        
        # 更新任务状态
        task.end_time = datetime.now()
        
        # 智能判断任务状态
        if return_code == 0:
            # 退出码为 0，认为成功
            task.status = TaskStatus.COMPLETED
            queue.logger.info(f"任务完成: {task.name}")
        elif return_code is not None and return_code != 0:
            # 有明确的非零退出码，检查日志确认是否真的失败
            log_status = self._check_log_for_status(task.log_file)
            if log_status is True:
                # 日志显示成功
                task.status = TaskStatus.COMPLETED
                queue.logger.info(f"任务完成: {task.name} (日志显示成功)")
            else:
                task.status = TaskStatus.FAILED
                task.error_message = f"退出码: {return_code}"
                queue.logger.error(f"任务失败: {task.name} ({task.error_message})")
        else:
            # 退出码为 None，通过日志判断
            log_status = self._check_log_for_status(task.log_file)
            if log_status is True:
                task.status = TaskStatus.COMPLETED
                queue.logger.info(f"任务完成: {task.name} (根据日志判断)")
            elif log_status is False:
                task.status = TaskStatus.FAILED
                task.error_message = "日志显示任务失败"
                queue.logger.error(f"任务失败: {task.name} ({task.error_message})")
            else:
                # 日志也无法判断，假设成功（保守策略：进程正常结束）
                task.status = TaskStatus.COMPLETED
                queue.logger.info(f"任务完成: {task.name} (进程已结束)")
        
        # 添加到历史
        queue.history_manager.add(task.to_dict())
        
        # 从任务列表移除
        with queue._lock:
            if task.id in queue.tasks:
                del queue.tasks[task.id]
        
        # 从持久化存储移除
        self._on_task_finished(task.id)
    
    def _generate_queue_id(self) -> str:
        """生成队列 ID"""
        return f"queue_{uuid.uuid4().hex[:8]}"
    
    # ============ 队列管理 ============
    
    def add_queue(self, name: str, yaml_path: str) -> Dict[str, Any]:
        """
        添加新队列
        
        Args:
            name: 队列名称
            yaml_path: YAML 配置文件路径
            
        Returns:
            队列配置信息
        """
        yaml_path = str(Path(yaml_path).resolve())
        
        # 检查文件是否存在
        if not Path(yaml_path).exists():
            raise ValueError(f"YAML 文件不存在: {yaml_path}")
        
        # 检查是否已添加
        for config in self.queue_configs.values():
            if config['yaml_path'] == yaml_path:
                raise ValueError(f"该 YAML 已添加为队列: {config['name']}")
        
        queue_id = self._generate_queue_id()
        config = {
            "id": queue_id,
            "name": name,
            "yaml_path": yaml_path,
            "created_at": datetime.now().isoformat()
        }
        
        # 加载队列
        self._load_queue(queue_id, config)
        
        # 保存配置
        self._save_workspace()
        
        logger.info(f"添加队列: {name} ({yaml_path})")
        return config
    
    def remove_queue(self, queue_id: str) -> bool:
        """
        移除队列（不删除文件）
        
        Args:
            queue_id: 队列 ID
            
        Returns:
            是否成功
        """
        if queue_id not in self.queues:
            return False
        
        # 停止队列
        queue = self.queues[queue_id]
        queue.stop_queue()
        queue.stop_all()
        
        # 移除
        del self.queues[queue_id]
        del self.queue_configs[queue_id]
        
        # 保存配置
        self._save_workspace()
        
        logger.info(f"移除队列: {queue_id}")
        return True
    
    def get_queue(self, queue_id: str) -> Optional[TaskManager]:
        """获取指定队列"""
        return self.queues.get(queue_id)
    
    def get_all_queues(self) -> List[Dict[str, Any]]:
        """获取所有队列信息"""
        result = []
        for queue_id, config in self.queue_configs.items():
            queue = self.queues.get(queue_id)
            if queue:
                info = {
                    **config,
                    "status": {
                        "queue_running": queue.queue_running,
                        "pending_count": len(queue.get_pending_tasks()),
                        "running_count": len(queue.get_running_tasks()),
                    }
                }
                result.append(info)
        return result
    
    def find_task_in_all_queues(self, task_id: str):
        """
        在所有队列中查找任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            (task, queue) 元组，如果未找到返回 (None, None)
        """
        for queue_id, queue in self.queues.items():
            task = queue.get_task(task_id)
            if task:
                return task, queue
        return None, None
    
    def find_task_in_history(self, task_id: str):
        """
        在所有队列的历史记录中查找任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            (task_dict, queue) 元组，如果未找到返回 (None, None)
        """
        for queue_id, queue in self.queues.items():
            # 获取所有历史记录（不限制数量）
            for task_dict in queue.get_history(limit=10000):
                if task_dict.get('id') == task_id:
                    return task_dict, queue
        return None, None
    
    # ============ 跨队列 GPU 检测 ============
    
    def get_global_gpu_usage(self) -> Dict[int, str]:
        """
        获取所有队列占用的 GPU
        
        Returns:
            {gpu_id: queue_name}
        """
        usage = {}
        for queue_id, queue in self.queues.items():
            queue_name = self.queue_configs[queue_id].get('name', queue_id)
            for gpu in queue.get_busy_gpus():
                usage[gpu] = queue_name
        return usage
    
    def check_cross_queue_conflict(self, queue_id: str, task_id: str) -> Optional[str]:
        """
        检查跨队列 GPU 冲突
        
        Args:
            queue_id: 队列 ID
            task_id: 任务 ID
            
        Returns:
            冲突描述，无冲突返回 None
        """
        queue = self.queues.get(queue_id)
        if not queue:
            return None
        
        task = queue.get_task(task_id)
        if not task or not task.gpu:
            return None
        
        current_queue_name = self.queue_configs[queue_id].get('name', queue_id)
        global_usage = self.get_global_gpu_usage()
        
        conflicts = []
        for gpu in task.gpu:
            if gpu in global_usage and global_usage[gpu] != current_queue_name:
                conflicts.append((gpu, global_usage[gpu]))
        
        if conflicts:
            gpus = ', '.join(str(g) for g, _ in conflicts)
            queues = ', '.join(set(q for _, q in conflicts))
            return f"GPU {gpus} 被 {queues} 占用中"
        
        return None
    
    # ============ 兼容单 YAML 模式 ============
    
    def add_single_yaml(self, yaml_path: str) -> str:
        """
        添加单个 YAML（兼容旧启动方式）
        
        Args:
            yaml_path: YAML 文件路径
            
        Returns:
            队列 ID
        """
        yaml_path = str(Path(yaml_path).resolve())
        name = Path(yaml_path).stem  # 使用文件名作为队列名
        
        # 如果已存在对应队列，返回其 ID
        for queue_id, config in self.queue_configs.items():
            if config['yaml_path'] == yaml_path:
                return queue_id
        
        config = self.add_queue(name, yaml_path)
        return config['id']
