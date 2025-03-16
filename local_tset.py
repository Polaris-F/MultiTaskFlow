from multitaskflow import TaskFlow

# 创建任务流管理器
manager = TaskFlow("examples/tasks.yaml")

# 启动任务流管理器
manager.run()