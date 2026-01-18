#!/usr/bin/env python
"""快速测试脚本"""
import sys
sys.path.insert(0, '.')

print("测试 1: 导入 manager 模块...")
from multitaskflow.web.manager import TaskManager, parse_gpu_from_command, Task, TaskStatus
print("✅ manager 导入成功")

print("\n测试 2: GPU 解析...")
result = parse_gpu_from_command('CUDA_VISIBLE_DEVICES=0,1 python train.py')
print(f"  解析 'CUDA_VISIBLE_DEVICES=0,1 python train.py' -> {result}")
assert result == [0, 1], f"期望 [0, 1]，得到 {result}"
print("✅ GPU 解析成功")

print("\n测试 3: 导入 server 模块...")
from multitaskflow.web.server import create_app
print("✅ server 导入成功")

print("\n测试 4: 创建 FastAPI 应用...")
app = create_app()
print(f"✅ FastAPI 应用创建成功: {app.title}")

print("\n" + "="*50)
print("🎉 所有测试通过！Phase 1 实现完成")
print("="*50)
