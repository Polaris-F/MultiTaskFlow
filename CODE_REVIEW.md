# MultiTaskFlow 代码 Review 报告

> **Review 时间**: 2026-02-09  
> **Review 范围**: 全量代码（CLI 核心、Web 后端、前端 React）  
> **版本**: v1.0.5

---

## 一、总览

| 模块 | 文件数 | 主要功能 |
|------|--------|---------|
| CLI 核心 | `task_flow.py`, `process_monitor.py` | 任务流编排、进程监控、消息推送 |
| Web 后端 | `server.py`, `manager.py`, `queue_manager.py`, `ws.py`, `notify.py`, `history.py`, `watcher.py`, `api/*.py` | FastAPI 服务、多队列管理、WebSocket 日志推送、认证 |
| Web 前端 | `App.tsx`, `stores/*.ts`, `api/index.ts`, `components/*.tsx` | React + Zustand + xterm.js |

整体架构清晰，CLI 模式和 Web 模式分离合理。以下按**严重程度**分类列出发现的问题。

---

## 二、严重问题 (High)

### H1. WebSocket 状态端点引用不存在的属性 `manager.history`

**文件**: [multitaskflow/web/ws.py](multitaskflow/web/ws.py#L276)

```python
"history_count": len(manager.history),
```

`TaskManager` 类没有 `history` 属性，历史记录通过 `manager.history_manager` 管理。应为：
```python
"history_count": manager.history_manager.count(),
```

此 bug 会导致 `/ws/status` WebSocket 端点在建立连接后立即抛出 `AttributeError`，状态实时推送完全不可用。

---

### H2. `Msg_push` 重试逻辑中 `time.sleep` 被执行两次

**文件**: [multitaskflow/process_monitor.py](multitaskflow/process_monitor.py#L118-L130)

在每次重试循环中，代码同时存在两处 `time.sleep(wait_time)`:
1. 循环开头（第 109 行）的指数退避等待
2. 遇到 429 状态码后额外的 `time.sleep(wait_time)`（第 121 行）
3. 循环末尾 `if attempt < max_retries - 1: time.sleep(wait_time)`（第 133 行）

在非 429 错误情况下，每次重试会等待 **两倍** 预期时间（循环开头 + 循环末尾各一次）。429 情况下会等待 **三倍**。

**修复建议**: 移除循环末尾的重复 `time.sleep`，只保留循环开头的退避逻辑。

---

### H3. `run_task` 中日志文件句柄泄漏

**文件**: [multitaskflow/web/manager.py](multitaskflow/web/manager.py#L755-L760)

```python
log_file = open(task.log_file, 'w', encoding='utf-8')
task.process = subprocess.Popen(
    task.command,
    shell=True,
    stdout=log_file,
    stderr=subprocess.STDOUT,
    ...
)
```

`log_file` 打开后传递给 `Popen`，但 **从未关闭**。`Popen` 不会在进程结束时自动关闭传入的文件对象。`_monitor_task` 中只调用了 `task.process.wait()` 而没有关闭文件句柄。

长时间运行会累积大量未关闭的文件描述符，最终可能触发 `OSError: Too many open files`。

**修复建议**: 在 `_monitor_task` 结束时关闭文件句柄，或使用 `with` 语句管理，或在 `task` 对象中保存文件句柄引用以便后续关闭。

---

### H4. 前端 API 层无 HTTP 错误检查

**文件**: [multitaskflow/web/frontend/src/api/index.ts](multitaskflow/web/frontend/src/api/index.ts)

所有 API 方法直接调用 `res.json()` 而不检查 `res.ok`。当后端返回 4xx/5xx 时：
- 若返回体非 JSON（如 HTML 错误页），`res.json()` 抛出未捕获异常
- 若返回 JSON 格式的错误对象，不符合 TypeScript 接口定义，导致下游逻辑异常

影响范围极广（所有 API 调用点）。

---

### H5. `retry_task` 搜索逻辑缺陷——无法从历史记录 retry

**文件**: [multitaskflow/web/api/execute.py](multitaskflow/web/api/execute.py#L65-L84)

```python
for queue in qm.queues.values():
    if queue.get_task(task_id):
        manager = queue
        break
```

`retry_task` API 只在各队列的 **活动任务** 中查找 (`get_task`)，而需要重试的任务通常已在 **历史记录** 中（已从 `tasks` dict 移除）。虽然 `manager.retry_task()` 方法内部会查找历史记录，但如果所有队列的 `get_task` 都返回 `None`，则 `manager` 回退到 `get_task_manager()` 返回的默认队列（通常是第一个队列），导致在**错误的队列**中执行 retry。

**修复建议**: 在查找任务时也搜索各队列的历史记录：
```python
for queue in qm.queues.values():
    if queue.get_task(task_id):
        manager = queue
        break
    # 也搜索历史记录
    for item in queue.history_manager.items:
        if item.get('id') == task_id:
            manager = queue
            break
```

---

## 三、中等问题 (Medium)

### M1. `reorder_tasks` 丢失非 pending 任务

**文件**: [multitaskflow/web/manager.py](multitaskflow/web/manager.py#L647-L656)

```python
def reorder_tasks(self, new_order: List[str]) -> bool:
    running_ids = [t.id for t in self.get_running_tasks()]
    self.task_order = running_ids + new_order
    return True
```

重排后 `task_order` 只包含 running + pending（new_order 中的），任何处于 stopped/failed 但仍在 `tasks` dict 中的任务都从 `task_order` 中丢失，导致后续 `get_all_tasks()` 不返回它们。

---

### M2. QueueTabs 运算符优先级 Bug

**文件**: [multitaskflow/web/frontend/src/components/QueueTabs.tsx](multitaskflow/web/frontend/src/components/QueueTabs.tsx#L53)

```tsx
queue.status?.running_count ?? 0 > 0
```

由于 `>` 优先级高于 `??`，实际等价于 `queue.status?.running_count ?? (0 > 0)` → `queue.status?.running_count ?? false`。队列运行状态指示灯逻辑错误。

**修复**: `(queue.status?.running_count ?? 0) > 0`

---

### M3. LogPanel WebSocket 消息解析无 try/catch

**文件**: [multitaskflow/web/frontend/src/components/LogPanel.tsx](multitaskflow/web/frontend/src/components/LogPanel.tsx#L200)

`ws.onmessage` 中直接 `JSON.parse(event.data)` 无异常处理。若服务端发送非 JSON 数据，将抛出未捕获异常导致日志面板功能中断。

---

### M4. ESC 快捷键穿透弹窗

**文件**: [multitaskflow/web/frontend/src/App.tsx](multitaskflow/web/frontend/src/App.tsx#L196-L203)

全局 ESC 监听会在任何弹窗（TaskDialog、TaskDetailDialog、SettingsPanel）打开时同时关闭日志面板。应检查是否有弹窗打开，或在弹窗内 `stopPropagation`。

---

### M5. `stop_task` 与 `_monitor_task` 竞态条件

**文件**: [multitaskflow/web/manager.py](multitaskflow/web/manager.py#L842-L876)

`stop_task` 和 `_monitor_task` 都会执行：
1. 设置 `task.status`
2. 调用 `history_manager.add(task.to_dict())`
3. `del self.tasks[task.id]`

如果 `stop_task` 和 `_monitor_task`（在进程被 kill 后 `wait()` 返回）几乎同时执行，可能导致：
- 历史记录被添加两次
- `KeyError` 当第二个 `del self.tasks[task.id]` 执行时

**修复建议**: 在 `_monitor_task` 中检查任务是否已被 `stop_task` 处理，或使用锁保护状态转换。

---

### M6. `_load_from_saved_tasks` 字段类型不匹配

**文件**: [multitaskflow/web/manager.py](multitaskflow/web/manager.py#L228-L236)

```python
task = Task(
    ...
    start_time=task_data.get('start_time'),  # 字符串 ISO 格式
    end_time=task_data.get('end_time'),       # 字符串 ISO 格式
    duration=task_data.get('duration'),       # float 秒数
    ...
)
```

`Task.start_time` 和 `Task.end_time` 的类型声明为 `Optional[datetime]`，但 JSON 反序列化后传入的是 ISO 格式字符串。`Task.get_duration()` 方法会尝试对字符串做 `datetime.now() - self.start_time` 运算，抛出 `TypeError`。`duration` 字段在 `Task` dataclass 中未声明。

---

### M7. SettingsPanel 设置项未生效

**文件**: [multitaskflow/web/frontend/src/components/SettingsPanel.tsx](multitaskflow/web/frontend/src/components/SettingsPanel.tsx)

`settingsStore` 中的列宽、自动隐藏列等设置 (`taskNameMinWidth`, `canHideCommand`, `tableWrapContent` 等) **未被 `TaskTable` 组件消费**。TaskTable 使用独立的硬编码列定义和内部 `columnWidths` state。这些设置面板选项对用户无实际效果。

---

### M8. TaskDetailDialog 重复 Toast 和异步问题

**文件**: [multitaskflow/web/frontend/src/components/TaskDetailDialog.tsx](multitaskflow/web/frontend/src/components/TaskDetailDialog.tsx#L73-L81)

- `handleDelete`: 调用 `deleteTask(task.id)` 后立即调用 `showToast('任务已删除')`，但 `deleteTask` 内部也会 `showToast('已删除')`，导致删除成功显示两个 toast
- `handleMove`: 调用 `moveTask()` 前就 `showToast('已上移'/'已下移')`，不等待结果

---

### M9. 通知设置的 `notification_enabled` 未被实际使用

**文件**: [multitaskflow/web/api/notification.py](multitaskflow/web/api/notification.py#L77-L95) + [multitaskflow/web/notify.py](multitaskflow/web/notify.py)

用户可以在设置面板中切换通知开关（`notification_enabled`），该值保存到 `.workspace.json`，但 `send_task_notification` 函数只检查 token 是否存在，**从未检查 `notification_enabled` 字段**。即使用户关闭了通知开关，通知仍然会发送。

---

## 四、低等问题 (Low)

### L1. CLI `_setup_logger` 重复添加 Handler

**文件**: [multitaskflow/task_flow.py](multitaskflow/task_flow.py#L215-L243)

每次创建 `TaskFlow` 实例都会向 `logging.getLogger("TaskFlow")` 添加新的 Handler。如果同一进程中多次实例化 `TaskFlow`，日志会重复输出。

---

### L2. CLI 日志固定写入 `logs/` 相对目录

**文件**: [multitaskflow/task_flow.py](multitaskflow/task_flow.py#L220-L222)

```python
if not os.path.exists("logs"):
    os.makedirs("logs")
```

日志目录相对于 CWD 创建，而非配置文件所在目录。如果用户从不同目录运行 `taskflow /some/path/tasks.yaml`，日志不会写入配置文件旁边。

---

### L3. `check_new_tasks` 不传递 `env` 参数

**文件**: [multitaskflow/task_flow.py](multitaskflow/task_flow.py#L695)

CLI 模式的 `check_new_tasks` 创建新 `Task` 时未传递 `env` 参数：
```python
task = Task(
    name=task_config['name'],
    command=task_config['command'],
    status=task_config.get('status', 'pending')
    # 缺少 env=task_config.get('env', {})
)
```

---

### L4. `_monitor_pid` 恢复任务使用当前时间作为 `start_time`

**文件**: [multitaskflow/web/queue_manager.py](multitaskflow/web/queue_manager.py#L267)

```python
task.start_time = datetime.now()
```

WebUI 重启后恢复的运行中任务使用重启时间作为 start_time，而非任务实际开始时间。`.workspace.json` 中保存了 `start_time` 但未使用。

---

### L5. 前端 `formatDuration` 0 秒显示为 `-`

**文件**: [multitaskflow/web/frontend/src/components/TaskTable.tsx](multitaskflow/web/frontend/src/components/TaskTable.tsx#L47)

```tsx
if (!seconds || seconds < 0) return '-';
```

`!seconds` 在 `seconds === 0` 时为 `true`，导致瞬时完成的任务显示 `-` 而非 `0s`。

---

### L6. AddQueueDialog 关闭后表单不重置

**文件**: [multitaskflow/web/frontend/src/components/AddQueueDialog.tsx](multitaskflow/web/frontend/src/components/AddQueueDialog.tsx#L11-L13)

用户填写表单后关闭弹窗，再次打开时旧数据仍在。应在 `onClose` 或 `useEffect` 中重置 state。

---

### L7. LogStreamer 的 `file_positions` 和 `line_buffers` 未被使用

**文件**: [multitaskflow/web/ws.py](multitaskflow/web/ws.py#L74-L77)

`LogStreamer` 类维护了实例级的 `file_positions` 和 `line_buffers` dict，但 `stream_log` 方法内使用了局部变量 `last_pos` 和 `line_buffer`。这些实例属性是死代码。

---

### L8. Toolbar 无防重复点击保护

**文件**: [multitaskflow/web/frontend/src/components/Toolbar.tsx](multitaskflow/web/frontend/src/components/Toolbar.tsx)

"检查 YAML"、"重新加载"、"停止所有"、"清空历史" 等操作按钮没有 loading 状态或防抖。快速双击会发送多次请求。

---

### L9. `XTerminal` 未使用的 `onContentUpdate` prop

**文件**: [multitaskflow/web/frontend/src/components/XTerminal.tsx](multitaskflow/web/frontend/src/components/XTerminal.tsx#L10)

接口中声明了 `onContentUpdate` 回调 prop，但组件内部从未调用。

---

### L10. Header 组件版本号硬编码

**文件**: [multitaskflow/web/frontend/src/components/Header.tsx](multitaskflow/web/frontend/src/components/Header.tsx#L14)

版本号 `v1.0.5` 硬编码在前端组件中，与 `pyproject.toml` 和 `__init__.py` 中的版本分开维护，容易漂移。建议通过 API 端点获取版本号。

---

### L11. `_init_` 版本号注释不一致

**文件**: [multitaskflow/__init__.py](multitaskflow/__init__.py#L13-L19)

文件头注释中写 `版本: 0.1.5`，但实际 `__version__ = '1.0.5'`。

---

### L12. LoginPage 误导性安全提示

**文件**: [multitaskflow/web/frontend/src/components/LoginPage.tsx](multitaskflow/web/frontend/src/components/LoginPage.tsx#L176)

页面底部显示 "🔒 连接已加密保护"，但应用默认通过 HTTP（非 HTTPS）运行，该提示不准确。

---

## 五、架构建议

### A1. CLI 与 Web 的 Task 类重复定义

CLI 的 `task_flow.Task` 和 Web 的 `manager.Task` 是两个完全独立的类定义。虽然两个模式的需求有差异（CLI 用 class，Web 用 dataclass），但核心字段高度重叠。建议抽取共享基类或使用 Mixin 避免定义漂移。

### A2. 全局状态管理 (`state.py`) 非线程安全

`get_task_manager()` 在无锁保护下通过 `_current_queue_id` 访问 `_queue_manager.queues`，而其他线程可能同时修改队列配置。在高并发场景下可能出现不一致。

### A3. `_save_workspace` 频繁写入 JSON

每次任务启动、完成、状态变化都会调用 `_save_workspace()` 写入完整的 `.workspace.json`。在多任务并发场景下，写入操作虽有锁保护，但 IO 可能成为性能瓶颈。建议改为定时批量写入（如每 5 秒）或使用轻量级嵌入式数据库。

### A4. 密码仅用 SHA-256 哈希

**文件**: [multitaskflow/web/api/auth.py](multitaskflow/web/api/auth.py#L82-L84)

```python
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```

无盐的 SHA-256 哈希容易被彩虹表攻击。建议使用 `bcrypt` 或 `argon2` 等专门的密码哈希算法。

### A5. Web 依赖 `pydantic` 未在 pyproject.toml 声明

FastAPI 依赖 pydantic，API 模型大量使用 `BaseModel`，但 `pyproject.toml` 的 `[web]` extras 只列了 `fastapi`, `uvicorn`, `watchdog`。虽然 FastAPI 会间接安装 pydantic，但显式声明更稳健。

---

## 六、问题汇总表

| # | 严重度 | 模块 | 问题摘要 |
|---|--------|------|---------|
| H1 | 🔴 High | Web 后端 | `ws.py` 引用不存在的 `manager.history` 属性 |
| H2 | 🔴 High | CLI | `Msg_push` 重试中 sleep 执行两次 |
| H3 | 🔴 High | Web 后端 | `run_task` 中日志文件句柄泄漏 |
| H4 | 🔴 High | 前端 | API 层无 HTTP 错误码检查 |
| H5 | 🔴 High | Web 后端 | `retry_task` API 多队列场景找错队列 |
| M1 | 🟡 Medium | Web 后端 | `reorder_tasks` 丢失非 pending 任务 |
| M2 | 🟡 Medium | 前端 | QueueTabs 运算符优先级 bug |
| M3 | 🟡 Medium | 前端 | WebSocket 消息解析无异常处理 |
| M4 | 🟡 Medium | 前端 | ESC 快捷键穿透弹窗 |
| M5 | 🟡 Medium | Web 后端 | `stop_task` 与 `_monitor_task` 竞态 |
| M6 | 🟡 Medium | Web 后端 | 恢复任务 `start_time` 类型不匹配 |
| M7 | 🟡 Medium | 前端 | SettingsPanel 设置项未实际生效 |
| M8 | 🟡 Medium | 前端 | TaskDetailDialog 重复 toast |
| M9 | 🟡 Medium | Web 后端 | `notification_enabled` 开关无效 |
| L1 | 🟢 Low | CLI | Logger Handler 重复添加 |
| L2 | 🟢 Low | CLI | 日志目录相对 CWD |
| L3 | 🟢 Low | CLI | `check_new_tasks` 缺少 env 参数 |
| L4 | 🟢 Low | Web 后端 | 恢复任务 start_time 不准确 |
| L5 | 🟢 Low | 前端 | 0 秒时长显示为 `-` |
| L6 | 🟢 Low | 前端 | AddQueueDialog 关闭不重置表单 |
| L7 | 🟢 Low | Web 后端 | LogStreamer 死代码 |
| L8 | 🟢 Low | 前端 | Toolbar 无防重复点击 |
| L9 | 🟢 Low | 前端 | XTerminal 未使用的 prop |
| L10 | 🟢 Low | 前端 | 版本号硬编码 |
| L11 | 🟢 Low | CLI | `__init__.py` 版本注释不一致 |
| L12 | 🟢 Low | 前端 | LoginPage 误导性安全提示 |

---

*Review by GitHub Copilot — 2026-02-09*
