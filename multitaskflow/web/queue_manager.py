#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
队列管理器

管理多个独立的任务队列，每个队列对应一个 YAML 配置文件。
支持跨队列 GPU 冲突检测。
"""

import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from .manager import TaskManager

logger = logging.getLogger("QueueManager")


class QueueManager:
    """
    队列管理器
    
    管理多个 TaskManager（现在称为 TaskQueue），每个对应一个 YAML 文件。
    提供跨队列 GPU 冲突检测和统一的队列管理接口。
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
        
        # 确保工作空间目录存在
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载工作空间配置
        self._load_workspace()
        
        logger.info(f"队列管理器初始化完成，工作空间: {self.workspace_dir}")
    
    def _load_workspace(self):
        """从 .workspace.json 加载队列配置"""
        if not self.workspace_file.exists():
            logger.info("工作空间配置文件不存在，创建新配置")
            self._save_workspace()
            return
        
        try:
            with open(self.workspace_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
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
                    
        except Exception as e:
            logger.error(f"加载工作空间配置失败: {e}")
    
    def _load_queue(self, queue_id: str, config: Dict[str, Any]):
        """加载单个队列"""
        yaml_path = config['yaml_path']
        # 历史文件在 YAML 所在目录的 logs/.history.json
        yaml_dir = Path(yaml_path).parent
        history_file = yaml_dir / "logs" / ".history.json"
        
        manager = TaskManager(yaml_path, str(history_file))
        self.queues[queue_id] = manager
        self.queue_configs[queue_id] = config
    
    def _save_workspace(self):
        """保存工作空间配置到 .workspace.json"""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "queues": list(self.queue_configs.values())
        }
        
        try:
            with open(self.workspace_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("工作空间配置已保存")
        except Exception as e:
            logger.error(f"保存工作空间配置失败: {e}")
    
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
