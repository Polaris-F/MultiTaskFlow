# MultiTaskFlow 多任务流管理工具

MultiTaskFlow 是一个轻量级的多任务流管理工具，用于按顺序执行和监控一系列任务。它可以帮助您管理数据处理、模型训练、评估等一系列需要顺序执行的任务，并提供实时状态更新和执行结果跟踪。

## ✨ 功能特点

### 🖥️ Web UI 可视化管理（v1.0.0 新增）
- **现代化界面**：全新的 React + TypeScript Web 界面
- **多队列管理**：同时管理多个任务队列
- **实时日志**：WebSocket 推送实时日志
- **任务操作**：创建、编辑、删除、排序任务
- **消息推送**：任务完成/失败时推送微信通知
- **认证保护**：密码保护，会话持久化

### 📟 CLI 命令行工具
- 基于YAML配置文件定义任务流
- 支持Python脚本和Shell命令的执行
- 提供任务状态实时监控
- 自动执行失败任务的重试逻辑
- 完整的日志记录和任务执行历史
- 进程PID跟踪与管理
- 优雅的信号处理和任务终止
- 支持静默模式，可跳过消息通知
- **智能环境变量加载**：优先从配置文件同目录查找 `.env` 文件
- **环境变量配置检查**：启动时自动显示环境变量配置状态
- **彩色输出支持**：可选安装 colorama 获得更友好的输出体验
- **后端状态查看** (v1.0.3)：`taskflow status` 查看运行中的后端服务
- **进程监控** (v1.0.3)：`taskflow monitor <pid>` 监控任意进程，结束后发送通知

## 安装方法

### 要求

- Python 3.7+
- PyYAML
- 其他依赖库（如有）

### 配置消息推送令牌和静默模式

#### 环境变量文件 (.env) 加载机制

MultiTaskFlow 采用智能的 `.env` 文件加载策略，按以下优先级查找：

1. **配置文件同目录**（推荐）：与 `tasks.yaml` 放在同一目录
   ```
   /your/project/
   ├── tasks.yaml
   └── .env          # 优先加载这个
   ```

2. **当前工作目录**：运行命令时的工作目录
   ```
   /current/directory/
   └── .env          # 次优先
   ```

3. **向上递归查找**：从当前目录向上查找直到找到 `.env` 文件

**优势**：
- 不同项目可以有独立的环境配置
- 配置文件和环境变量放在一起，便于管理
- 启动时会显示加载的 `.env` 文件位置，方便确认

#### 环境变量配置检查

启动时，MultiTaskFlow 会自动显示环境变量配置状态：

```
============================================================
                    [环境变量配置检查]
============================================================
  .env 文件: /path/to/your/.env
  MSG_PUSH_TOKEN: AT_abc123...xyz789 (已配置)
  MTF_SILENT_MODE: false (消息推送已启用)
============================================================
```

- Token 会脱敏显示（仅显示前后各6位）
- 如果未找到 `.env` 文件，会提示推荐的创建位置
- 运行过程中修改 `.env` 文件，下一个任务会自动检测并显示变化

#### 消息推送令牌

在使用消息推送功能前，需要配置 MSG_PUSH_TOKEN 环境变量。以下是配置方法：

##### 1. 推荐方式：在配置文件同目录创建 .env 文件

在您的任务配置文件（如 `tasks.yaml`）同目录下创建 `.env` 文件：

```bash
# .env 文件内容
MSG_PUSH_TOKEN=your_pushplus_token_here
MTF_SILENT_MODE=false
```

**优势**：配置随项目走，不影响其他项目。

##### 2. 永久配置（全局）

在 `~/.bashrc` 或 `~/.zshrc` 文件中添加：

```bash
# MultiTaskFlow 消息推送配置
export MSG_PUSH_TOKEN="your_pushplus_token_here"
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

##### 3. 临时配置

在运行命令前设置：
```bash
MSG_PUSH_TOKEN=your_token python your_script.py
```

#### 静默模式配置

如果您不希望收到消息通知，可以启用静默模式。

##### 1. 推荐方式：在 .env 文件中配置

```bash
# .env 文件内容
MTF_SILENT_MODE=true
```

##### 2. 永久配置静默模式（全局）

在 `~/.bashrc` 或 `~/.zshrc` 文件中添加：

```bash
# MultiTaskFlow 静默模式配置
export MTF_SILENT_MODE=true
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

##### 3. 临时配置静默模式

在运行命令前设置：
```bash
MTF_SILENT_MODE=true taskflow your_tasks.yaml
```

**支持的值**：
- 启用静默模式：`true`, `1`, `yes`, `on`
- 禁用静默模式：`false`, `0`, `no`, `off` 或不设置

#### 获取 Token

1. 访问 [PushPlus 官网](https://www.pushplus.plus/)
2. 注册并登录
3. 在个人中心获取您的 token

### （方法1）从PyPI安装

```bash
# 基础安装（仅 CLI 命令行工具）
pip install multitaskflow

# 完整安装（CLI + Web UI）⭐ 推荐
pip install multitaskflow[web]

# 安装并启用彩色输出
pip install multitaskflow[color]

# 全部功能
pip install multitaskflow[web,color]
```

**Web UI 功能**：
- 安装 `web` 扩展后，可使用 `taskflow web` 命令启动可视化管理界面
- 包含 FastAPI + React 前端，支持多队列管理、实时日志、消息推送等功能

**彩色输出功能**：
- 安装 `colorama` 后，环境变量配置检查会以彩色显示
- 绿色表示已配置，红色表示未设置，黄色表示警告
- 如果不安装，会自动回退到普通文本输出，完全不影响功能

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

### 2. （方法三）使用 Web UI【推荐：可视化管理，支持多队列】

启动 Web UI 可视化管理界面：

```bash
# 使用当前目录作为工作空间
taskflow web

# 加载指定 YAML 配置文件
taskflow web tasks.yaml

# 指定端口
taskflow web --port 9000

# 指定工作空间目录
taskflow web -w /path/to/workspace

# 查看帮助
taskflow web --help
```

**Web UI 功能**：
- 📋 多队列管理：同时管理多个任务队列
- ✏️ 任务操作：创建、编辑、删除、排序任务
- ▶️ 执行控制：单任务执行、队列自动执行
- 📊 实时日志：WebSocket 推送实时日志
- 🔔 消息推送：任务完成/失败时推送微信通知
- 🔐 认证保护：首次使用需设置密码

### 2. （方法四）查看后端状态 (v1.0.3)

查看当前运行中的 MultiTaskFlow 后端服务：

```bash
taskflow status
```

**输出示例**：
```
=== MultiTaskFlow 后端状态 ===

发现 1 个运行中的后端:

  [1] PID: 12345
      端口: http://localhost:8080
      工作区: /path/to/workspace
      运行时长: 2h30m
```

### 2. （方法五）进程监控 (v1.0.3)

监控任意进程，进程结束后发送 PushPlus 通知：

```bash
# 基础用法 - 监控指定 PID
taskflow monitor 12345

# 指定进程名称（用于通知）
taskflow monitor 12345 --name "训练任务"

# 静默模式（只打印，不发送通知）
taskflow monitor 12345 --silent

# 查看帮助
taskflow monitor --help
```

**使用场景**：
- 监控长时间运行的训练进程
- 监控非 MultiTaskFlow 管理的任务
- 在后台监控任务完成后收到微信通知

### 2. （方法六）使用sh脚本工具【使用场景：需要后台运行，通过log查看输出】
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
  status: "pending"  # pending, running, completed, failed, skipped
  retry: 3  # 失败后重试次数 (TODO)
  timeout: 3600  # 任务超时时间（秒）(TODO)
  depends_on: ["前置任务名称"]  # 依赖的任务 (TODO)
```

**status 字段说明**：
- `pending`: 待执行（默认值）
- `running`: 执行中（系统自动设置）
- `completed`: 已完成（系统自动设置）
- `failed`: 执行失败（系统自动设置）
- `skipped`: 跳过执行（手动设置，加载时会被过滤）

**使用 skipped 状态**：
如果您不想执行某个任务，可以在配置文件中将其 status 设置为 `skipped`，该任务将不会被加载到执行队列中。

```yaml
- name: "临时禁用的任务"
  command: "python old_script.py"
  status: "skipped"  # 这个任务不会执行
```

### 静默模式

MultiTaskFlow 支持静默模式，在此模式下不会发送任何消息通知。这对于以下场景非常有用：

- **生产环境部署**：在生产环境中运行时，可能不需要消息通知
- **调试阶段**：开发和调试过程中避免频繁接收通知
- **批量任务**：执行大量批处理任务时，只关注最终结果而非每个任务
- **CI/CD 流程**：在自动化构建流水线中使用，避免触发过多通知

#### 启用静默模式

静默模式通过环境变量 `MTF_SILENT_MODE` 控制：

```bash
# 启用静默模式
export MTF_SILENT_MODE=true

# 临时启用
MTF_SILENT_MODE=true taskflow tasks.yaml
```

支持的值：
- 设为 `true`, `1`, `yes`, `on` 表示启用静默模式
- 不设置或设为其他值表示禁用静默模式

#### 静默模式的工作原理

当启用静默模式时：
1. 所有任务执行完成后不会发送消息通知
2. 任务管理器完成时不会发送总结报告
3. 所有操作和结果仍会记录在日志文件中
4. 控制台输出不受影响，仍然会显示所有信息

注意，静默模式只影响消息通知行为，不会改变任务的实际执行过程。

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

## TODO / 计划中的功能

### 🔄 动态任务管理（计划中）

**功能描述**：支持运行时监控配置文件变化，实现任务的动态增删改

**实现方案**：
- 使用 `watchdog` 库监控 YAML 配置文件变化
- 基于任务 ID 的增量更新机制
- 支持以下动态操作：
  - ✅ **新增任务**：在配置中添加新任务（需有唯一 ID）会自动加入执行队列
  - ✅ **标记跳过**：将任务 status 改为 `skipped` 可从队列中移除
  - ✅ **删除任务**：从配置中删除的任务会从队列中移除
  - ✅ **更新参数**：修改现有任务参数（保持 ID 不变）会更新队列中的任务

**配置要求**：
```yaml
# 每个任务必须有唯一的 id 字段
tasks:
  - id: task_a          # 必须唯一
    name: "数据预处理"
    command: "python preprocess.py"
    status: pending     # pending | running | completed | failed | skipped
    
  - id: task_b
    name: "模型训练"
    command: "python train.py"
    status: pending
    
  - id: task_c
    name: "旧任务"
    status: skipped     # 标记为跳过，不会执行
```

**使用场景**：
1. 长时间运行的任务流中，临时禁用某些任务
2. 根据前面任务的结果动态添加新任务
3. 修正配置错误而不需要重启整个流程

**技术实现**：
- 依赖：`watchdog>=2.1.0`
- 核心逻辑：文件变化监听 + ID 去重 + 队列增量更新
- 日志输出：实时显示任务的添加、移除、更新操作

**当前状态**：设计阶段，欢迎反馈和建议

### 📊 GPU 监控面板（计划中）

**功能描述**：在 Web UI 中集成 GPU 状态监控，实时显示每张显卡的使用情况

**界面设计**：
- **顶部状态栏**：快速预览所有 GPU 状态（利用率 + 显存）
- **独立详情页**：点击进入，查看每张卡的详细信息和进程列表

**显示内容**：
- GPU 利用率（百分比 + 进度条）
- 显存使用量（已用/总量）
- 温度、风扇转速、功耗
- 运行中的进程列表（PID、用户、命令、显存占用）

**技术方案**：
- 依赖：`nvitop>=1.0.0`（可选依赖 `pip install multitaskflow[gpu]`）
- 后端 API：`/api/gpu/status`
- 前端组件：`GpuStatusBar.tsx` + `GpuDetailPage.tsx`
- 实时更新：WebSocket 每 2 秒推送

**当前状态**：设计完成，待实现

---

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

- **1.0.3** - 2026-02-05
  - ✨ **`taskflow status`**：查看运行中的后端服务状态（PID、端口、工作区、运行时长）
  - ✨ **`taskflow monitor <pid>`**：监控任意进程，结束后发送 PushPlus 通知
  - 支持 `--name` 自定义通知中的进程名称
  - 支持 `--silent` 静默模式（不发送通知）

- **1.0.2** - 2026-02-05
  - 🐛 修复任务去重检查不包含历史记录的问题
  - 🐛 修复重启后队列中等待任务丢失的问题
  - 🐛 修复 `load-selected-tasks` API 缺少去重检查的问题
  - 改进工作空间持久化机制

- **1.0.1** - 2026-01-21
  - 若干 Bug 修复和改进

- **1.0.0** - 2026-01-18 🎉 正式发布
  - 🖥️ **Web UI 可视化管理界面**：全新的 React + TypeScript 前端
  - 📟 **CLI 集成**：`taskflow web` 命令一键启动 Web UI
  - 📋 **多队列管理**：支持同时管理多个任务队列
  - 🔔 **消息推送**：集成 PushPlus，任务完成/失败时推送微信通知
  - 🔐 **认证保护**：密码保护 + 会话持久化
  - 📊 **实时日志**：WebSocket 推送实时日志

- **0.1.5** - 2025-11-10
  - 任务跳过功能（status: skipped）
  - 智能环境变量加载

- **0.1.4** - 2025-11-10
  - 环境变量配置检查
  - 彩色输出支持

## 许可证

本项目采用MIT许可证 - 详情请查看 [LICENSE](LICENSE) 文件

## 作者与致谢

- **主要开发者**: [Polaris](https://github.com/Polaris-F)
- 感谢所有贡献者和使用者的宝贵反馈