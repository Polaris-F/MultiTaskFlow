# MultiTaskFlow 多任务流管理工具

MultiTaskFlow 是一个轻量级的多任务流管理工具，用于按顺序执行和监控一系列任务。它可以帮助您管理数据处理、模型训练、评估等一系列需要顺序执行的任务，并提供实时状态更新和执行结果跟踪。

## 功能特点

- 基于YAML配置文件定义任务流
- 支持Python脚本和Shell命令的执行
- 提供任务状态实时监控
- 自动执行失败任务的重试逻辑
- 支持任务之间的依赖关系
- 完整的日志记录和任务执行历史
- 进程PID跟踪与管理
- 优雅的信号处理和任务终止

## 安装方法

### 要求

- Python 3.7+
- PyYAML
- 其他依赖库（如有）

### 配置消息推送令牌

在使用消息推送功能前，需要配置 MSG_PUSH_TOKEN 环境变量。以下是配置方法：

#### 1. 永久配置（推荐）

在 `~/.bashrc` 或 `~/.zshrc` 文件中添加：

```bash
# MultiTaskFlow 消息推送配置
export MSG_PUSH_TOKEN="your_pushplus_token_here"
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

#### 2. 临时配置

在运行命令前设置：
```bash
MSG_PUSH_TOKEN=your_token python your_script.py
```

#### 3. 开发模式配置

在项目根目录创建 `.env` 文件：
```bash
echo "MSG_PUSH_TOKEN=your_token" > .env
```

#### 获取 Token

1. 访问 [PushPlus 官网](https://www.pushplus.plus/)
2. 注册并登录
3. 在个人中心获取您的 token

### （方法1）从PyPI安装

```bash
# 使用pip直接安装
pip install multitaskflow
```

### （方法2）从源码安装

```bash
# 克隆仓库
git clone https://github.com/Polaris-F/MultiTaskFlow.git
cd MultiTaskFlow

# 方法1: 使用pip直接安装
pip install .

# 方法2: 开发模式安装
pip install -e .
```

### （方法3）构建离线包方法

如果您想构建wheel包或源码分发包，可以使用以下命令：

```bash
# 安装构建工具
pip install build

# 构建分发包
python -m build

# 构建的包会在dist/目录下生成
```

## 使用方法

**如果需要使用 消息接收功能，请访问 https://www.pushplus.plus/ 获取您的token**

### 1. 创建任务配置文件

创建一个YAML格式的任务配置文件，定义您要执行的任务序列：

```yaml
# tasks.yaml 示例
- name: "任务1-数据准备"
  command: "python scripts/prepare_data.py --input data/raw --output data/processed"
  status: "pending"

- name: "任务2-模型训练"
  command: "python scripts/train_model.py --data data/processed --epochs 10"
  status: "pending"

- name: "任务3-结果评估"
  command: "python scripts/evaluate.py --model-path models/latest.pt"
  status: "pending"
```

### 2. （方法一）使用Python API (推荐使用方法二、三)

在您的Python代码中使用MultiTaskFlow：

```python
from multitaskflow import TaskFlow

# 创建任务流管理器
task_manager = TaskFlow("path/to/your/tasks.yaml")

# 启动任务执行
task_manager.run()

# 您也可以动态添加任务
task_manager.add_task_by_config(
    name="额外任务", 
    command="echo '这是一个动态添加的任务'"
)
```

### 2. （方法二）使用命令行工具【使用场景：不需要后台运行，可实时查看输出】

安装后，您可以直接使用`taskflow`命令行工具：

```bash
# 使用配置文件运行任务流
taskflow path/to/your/tasks.yaml

# 使用默认配置
# 如果不提供配置文件路径，将在examples/tasks.yaml创建示例配置
taskflow

# 查看帮助
taskflow --help
```
### 2. （方法三）使用sh脚本工具【使用场景：需要后台运行，通过log查看输出】
首先```taskflowPro.sh```修改脚本中 ```TASK_CONFIG```为任务流yaml路径
```bash
chmod +x taskflowPro.sh
./taskflowPro.sh start  # 开始运行
./taskflowPro.sh stop   # 结束运行
```

## 效果展示

您可以运行我们提供的演示脚本，查看任务管理和消息接收的实际效果。演示脚本模拟了一个完整的深度学习工作流，包括数据预处理、模型训练、模型评估和数据归档等步骤。

### 运行演示脚本

```bash
# 安装完成后，直接运行示例脚本
python -m multitaskflow.examples.demo

# 或使用命令行工具
taskflow examples/tasks.yaml
```

### 演示内容

演示脚本将依次执行以下任务：

1. **数据预处理** - 模拟数据集加载、清洗和处理过程
2. **模型训练-阶段1** - 模拟第一阶段模型训练过程
3. **模型评估-阶段1** - 模拟对第一阶段训练模型的评估
4. **模型训练-阶段2** - 模拟基于第一阶段模型继续训练
5. **模型评估-阶段2** - 模拟对第二阶段训练模型的评估
6. **数据归档** - 模拟模型和结果数据的归档过程

每个任务都会显示详细的执行进度和模拟输出，让您直观了解MultiTaskFlow的任务管理能力。所有演示任务都是模拟执行，不会创建实际文件或占用大量资源。

### 期望效果

运行示例后，您将看到：

- 任务管理器启动和初始化过程
- 任务状态的实时更新（等待中→执行中→完成/失败）
- 每个任务的详细输出和进度信息
- 任务完成后的状态汇总

通过观察演示效果，您可以了解MultiTaskFlow如何帮助管理复杂的多步骤工作流程，以及它如何提供清晰的任务执行状态和结果反馈。

### 运行效果截图

![任务管理和执行效果](https://raw.githubusercontent.com/Polaris-F/MultiTaskFlow/main/images/demo_screenshot.png)

*实际运行时在控制台中会看到详细的输出，显示任务状态和进度信息*

## 高级功能（TODO）

### 任务配置选项

任务配置文件支持以下选项：

```yaml
- name: "示例任务"
  command: "python script.py"
  status: "pending"  # pending, running, completed, failed
  retry: 3  # 失败后重试次数
  timeout: 3600  # 任务超时时间（秒）
  depends_on: ["前置任务名称"]  # 依赖的任务
  env:  # 环境变量设置
    KEY1: "VALUE1"
    KEY2: "VALUE2"
```

### 自定义通知

您可以配置系统在任务状态变更时发送通知：

```python
from multitaskflow import TaskFlow, Msg_push

# 创建消息推送实例
notifier = Msg_push(
    webhook_url="your_webhook_url",
    channel="your_channel"
)

# 创建带通知功能的任务流管理器
task_manager = TaskFlow(
    "tasks.yaml",
    msg_push=notifier
)
```

## 自定义与扩展

MultiTaskFlow设计为可扩展的，您可以：

- 自定义任务状态处理逻辑
- 添加新的任务类型
- 扩展监控和报告功能

### 自定义任务处理器示例

```python
from multitaskflow import TaskFlow

class CustomTaskFlow(TaskFlow):
    def process_task_output(self, task, output):
        # 自定义输出处理逻辑
        print(f"处理任务 {task.name} 的输出: {output}")
        # 继续处理...
        super().process_task_output(task, output)
```

## 常见问题（FAQ）

**Q: XXXX？**

## 贡献指南

欢迎贡献代码、报告问题或提出新功能建议！

1. Fork 这个仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request

## 版本历史

- **1.0.0** - 2024-03-15
  - 首次发布
  - 基本任务管理功能
  - 命令行工具支持

## 许可证

本项目采用MIT许可证 - 详情请查看 [LICENSE](LICENSE) 文件

## 作者与致谢

- **主要开发者**: [Polaris](https://github.com/Polaris-F)
- 感谢所有贡献者和使用者的宝贵反馈 