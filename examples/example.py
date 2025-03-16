#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MultiTaskFlow 简单入门示例
此脚本展示了如何使用 MultiTaskFlow 管理和执行多个任务
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from multitaskflow import TaskFlow

def main():
    """主函数"""
    print("=" * 50)
    print("MultiTaskFlow 入门示例")
    print("=" * 50)
    
    # 使用示例任务配置文件
    config_path = os.path.join(os.path.dirname(__file__), "tasks.yaml")
    
    if not os.path.exists(config_path):
        print(f"错误: 找不到配置文件 {config_path}")
        print("请先确保已创建示例配置文件")
        return
    
    print(f"使用配置文件: {config_path}")
    print("即将启动任务流管理器...")
    time.sleep(1)
    
    try:
        # 创建任务流管理器
        manager = TaskFlow(config_path)
        
        # 可选: 动态添加一个额外任务
        manager.add_task_by_config(
            name="示例附加任务",
            command="echo '这是一个动态添加的任务' && sleep 2"
        )
        
        # 启动任务流管理器
        manager.run()
        
    except KeyboardInterrupt:
        print("\n用户中断，正在停止任务...")
        if 'manager' in locals():
            manager.stop()
    except Exception as e:
        print(f"发生错误: {str(e)}")
        if 'manager' in locals():
            manager.stop()

if __name__ == "__main__":
    main() 