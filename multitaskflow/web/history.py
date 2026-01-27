#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
执行历史持久化模块

将任务执行历史保存到 JSON 文件，支持持久化和恢复。
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict

logger = logging.getLogger("History")


class HistoryManager:
    """执行历史管理器"""
    
    def __init__(self, history_file: str, max_items: int = 100):
        """
        初始化历史管理器
        
        Args:
            history_file: 历史记录文件路径
            max_items: 最大保存条目数
        """
        self.history_file = Path(history_file)
        self.max_items = max_items
        self.items: List[Dict[str, Any]] = []
        
        # 确保目录存在
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载历史
        self._load()
    
    def _load(self):
        """从文件加载历史"""
        if not self.history_file.exists():
            self.items = []
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.items = data.get('history', [])
                logger.info(f"已加载 {len(self.items)} 条历史记录")
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            self.items = []
    
    def _save(self):
        """保存历史到文件"""
        try:
            data = {
                'updated_at': datetime.now().isoformat(),
                'history': self.items[-self.max_items:]  # 只保留最新的
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
    
    def add(self, task_data: Dict[str, Any]):
        """
        添加历史记录
        
        Args:
            task_data: 任务数据字典
        """
        # 清理不需要的字段
        record = {
            'id': task_data.get('id'),
            'name': task_data.get('name'),
            'command': task_data.get('command'),
            'status': task_data.get('status'),
            'gpu': task_data.get('gpu'),
            'start_time': task_data.get('start_time'),
            'end_time': task_data.get('end_time'),
            'duration': task_data.get('duration'),
            'error_message': task_data.get('error_message'),
            'log_file': task_data.get('log_file'),
            'note': task_data.get('note'),
        }
        
        self.items.append(record)
        
        # 限制数量
        if len(self.items) > self.max_items:
            self.items = self.items[-self.max_items:]
        
        # 保存
        self._save()
        logger.info(f"历史记录已添加: {record['name']}")
    
    def get_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Args:
            limit: 返回数量限制
        
        Returns:
            历史记录列表（最新在前）
        """
        return list(reversed(self.items[-limit:]))
    
    def clear(self):
        """清空历史记录"""
        self.items = []
        self._save()
        logger.info("历史记录已清空")
    
    def count(self) -> int:
        """获取历史记录数量"""
        return len(self.items)
    
    def remove(self, task_id: str) -> bool:
        """
        从历史记录中删除任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功删除
        """
        for i, item in enumerate(self.items):
            if item.get('id') == task_id:
                removed = self.items.pop(i)
                self._save()
                logger.info(f"从历史删除: {removed.get('name')} (ID: {task_id})")
                return True
        return False
    
    def update_note(self, task_id: str, note: str) -> bool:
        """
        更新历史记录中任务的备注
        
        Args:
            task_id: 任务ID
            note: 新备注
        
        Returns:
            是否成功更新
        """
        for item in self.items:
            if item.get('id') == task_id:
                item['note'] = note
                self._save()
                logger.info(f"更新历史备注: {item['name']} (ID: {task_id})")
                return True
        return False
