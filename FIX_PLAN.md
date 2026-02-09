# MultiTaskFlow 修复计划

> 基于 CODE_REVIEW.md 整理的修改指令，按优先级排列。每条给出明确的修改位置和修改方式。

---

## 严重问题 (必须修复)

### H1. 修复 `ws.py` 中 `manager.history` 属性引用错误

**文件**: `multitaskflow/web/ws.py`，`websocket_status` 函数内（约第 276 行）

**现状**:
```python
"history_count": len(manager.history),
```

**改为**:
```python
"history_count": manager.history_manager.count(),
```

---

### H2. 修复 `Msg_push` 重试逻辑中重复 sleep

**文件**: `multitaskflow/process_monitor.py`，`Msg_push` 函数

**问题**: 循环开头有一次 `time.sleep(wait_time)`，循环末尾 `if attempt < max_retries - 1: time.sleep(wait_time)` 又一次。非 429 场景下每次重试等待两倍时间。

**修改方式**: 删除循环末尾的 `if attempt < max_retries - 1: time.sleep(wait_time)` 这段（约第 133-134 行），只保留循环开头（约第 109-111 行）的退避等待。同时 429 分支里的额外 `time.sleep(wait_time)` 也是多余的（因为 `continue` 后循环开头已经会等待），一并删除第 121 行的 `time.sleep(wait_time)`。

---

### H3. 修复 `run_task` 中日志文件句柄泄漏

**文件**: `multitaskflow/web/manager.py`，`run_task` 方法

**现状**: 约第 755 行 `log_file = open(task.log_file, 'w', encoding='utf-8')` 打开文件后传给 `Popen`，但从未关闭。

**修改方式**:
1. 在 `Task` dataclass 中新增一个字段 `_log_fh` (不参与序列化) 用于保存文件句柄引用，或直接在 `run_task` 中将打开的文件对象保存到 task 上（如 `task._log_fh = log_file`）
2. 在 `_monitor_task` 方法中，`task.process.wait()` 之后添加关闭逻辑：
```python
# 关闭日志文件句柄
if hasattr(task, '_log_fh') and task._log_fh:
    try:
        task._log_fh.close()
    except Exception:
        pass
```
3. `stop_task` 方法中同样需要关闭文件句柄。

---

### H4. 前端 API 层增加 HTTP 错误检查

**文件**: `multitaskflow/web/frontend/src/api/index.ts`

**修改方式**: 添加一个统一的响应处理函数，所有 API 方法使用它：

```typescript
async function handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
        let message = `HTTP ${res.status}`;
        try {
            const data = await res.json();
            message = data.detail || data.message || message;
        } catch {
            // 响应体非 JSON，保持 HTTP 状态码错误信息
        }
        throw new Error(message);
    }
    return res.json();
}
```

然后将所有 `return res.json()` 改为 `return handleResponse(res)`。例如：
```typescript
async getTasks(): Promise<TasksResponse> {
    const res = await fetch(`${BASE_URL}/api/tasks`);
    return handleResponse<TasksResponse>(res);
},
```

对所有方法统一替换即可。

---

### H5. 修复 `retry_task` API 多队列查找逻辑

**文件**: `multitaskflow/web/api/execute.py`，`retry_task` 函数（约第 65-84 行）

**现状**: 只通过 `queue.get_task(task_id)` 在活动任务中查找，但需要 retry 的任务通常已在历史记录中。

**改为**:
```python
if qm:
    for queue in qm.queues.values():
        # 先在活动任务中找
        if queue.get_task(task_id):
            manager = queue
            break
        # 再在历史记录中找
        for item in queue.history_manager.items:
            if item.get('id') == task_id:
                manager = queue
                break
        if manager is not None:
            break
```

---

## 中等问题

### M1. 修复 `reorder_tasks` 丢失非 pending 任务

**文件**: `multitaskflow/web/manager.py`，`reorder_tasks` 方法

**现状**:
```python
running_ids = [t.id for t in self.get_running_tasks()]
self.task_order = running_ids + new_order
```

**改为**: 保留原 `task_order` 中不在 running 和 new_order 中的其他任务 ID：
```python
running_ids = [t.id for t in self.get_running_tasks()]
reordered_set = set(running_ids) | set(new_order)
other_ids = [tid for tid in self.task_order if tid not in reordered_set]
self.task_order = running_ids + new_order + other_ids
```

---

### M2. 修复 QueueTabs 运算符优先级

**文件**: `multitaskflow/web/frontend/src/components/QueueTabs.tsx`（约第 53 行）

**现状**:
```tsx
queue.status?.running_count ?? 0 > 0
```

**改为**:
```tsx
(queue.status?.running_count ?? 0) > 0
```

---

### M3. LogPanel WebSocket 消息加 try/catch

**文件**: `multitaskflow/web/frontend/src/components/LogPanel.tsx`，`ws.onmessage` 回调中

在 `JSON.parse(event.data)` 外包裹 try/catch：
```typescript
ws.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        // ... 现有处理逻辑
    } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
    }
};
```

---

### M4. ESC 快捷键增加弹窗判断

**文件**: `multitaskflow/web/frontend/src/App.tsx`（约第 196-203 行）

在 ESC handler 中增加判断，当有弹窗打开时不关闭日志面板：
```typescript
const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && currentLogId) {
        // 如果有弹窗打开，不处理（让弹窗自己处理 ESC）
        if (isTaskDialogOpen || isAddQueueDialogOpen) return;
        // 还需要检查 SettingsPanel 的 isSettingsOpen
        handleCloseLog();
    }
};
```

需要从 `useSettingsStore` 引入 `isSettingsOpen`，另外 TaskDetailDialog 的打开状态需要也得能检测到（可以从 DOM 判断或提升 state）。

---

### M5. 修复 `stop_task` 与 `_monitor_task` 竞态

**文件**: `multitaskflow/web/manager.py`

在 `_monitor_task` 中，处理任务完成逻辑前检查任务状态：
```python
# 在 _monitor_task 的状态更新部分
with self._lock:
    # 如果任务已被 stop_task 处理，跳过
    if task.id not in self.tasks:
        return
    if task.status == TaskStatus.STOPPED:
        return
    
    # ... 原有的状态更新、历史记录添加、删除任务逻辑
```

同时将 `stop_task` 中对 `self.tasks` 的删除也移到 `self._lock` 保护内（目前已经是）。

---

### M6. 修复 `_load_from_saved_tasks` 字段类型

**文件**: `multitaskflow/web/manager.py`，`_load_from_saved_tasks` 方法

`start_time` 和 `end_time` 从 JSON 恢复后是 ISO 字符串，需要转换为 `datetime` 对象：
```python
# 解析日期时间字段
start_time = task_data.get('start_time')
if isinstance(start_time, str):
    try:
        start_time = datetime.fromisoformat(start_time)
    except (ValueError, TypeError):
        start_time = None

end_time = task_data.get('end_time')
if isinstance(end_time, str):
    try:
        end_time = datetime.fromisoformat(end_time)
    except (ValueError, TypeError):
        end_time = None
```

另外 `Task` dataclass 没有 `duration` 字段，不要传 `duration=task_data.get('duration')` 给构造函数，删除这行。

---

### M7. 让 SettingsPanel 设置实际生效，或移除无效选项

**文件**: `multitaskflow/web/frontend/src/components/SettingsPanel.tsx` + `TaskTable.tsx`

**两种方案任选其一**:

**方案 A（推荐）**: 移除 SettingsPanel 中与表格列相关的无效设置项（`taskNameMinWidth`, `canHideCommand`, `canHideDuration`, `canHideActions`, `canHideNote`, `tableWrapContent`），只保留通知设置。同时清理 `settingsStore.ts` 中对应字段。

**方案 B**: 在 `TaskTable.tsx` 中消费 `settingsStore` 的设置值，将其应用到列宽和显隐控制。

---

### M8. 修复 TaskDetailDialog 重复 Toast

**文件**: `multitaskflow/web/frontend/src/components/TaskDetailDialog.tsx`

1. `handleDelete` 中删除本地的 `showToast('任务已删除', 'success')`，让 store 的 `deleteTask` 负责 toast。同时 `await deleteTask(task.id)` 确保异步完成后再 `onClose()`
2. `handleMove` 中删除本地的 `showToast`，改为 `await moveTask(...)` 后再决定是否显示提示

---

### M9. 让通知开关 `notification_enabled` 实际生效

**文件**: `multitaskflow/web/notify.py`，`send_task_notification` 函数

在获取 token 之前，先检查 `notification_enabled`：
```python
def send_task_notification(..., workspace_dir=None):
    # 先检查通知是否被用户关闭
    if workspace_dir:
        workspace_file = workspace_dir / ".workspace.json"
        if workspace_file.exists():
            try:
                import json
                data = json.loads(workspace_file.read_text())
                if not data.get("notification_enabled", True):
                    logger.debug("通知已被用户关闭，跳过")
                    return False
            except Exception:
                pass
    
    # ... 原有逻辑
```

注意 `queue_manager.py` 中的 `_send_task_notification` 也调了同一个函数，所以只改这一处即可。

---

## 低等问题

### L1. 修复 Logger Handler 重复添加

**文件**: `multitaskflow/task_flow.py`，`_setup_logger` 方法

在添加 handler 前检查是否已有：
```python
logger = logging.getLogger("TaskFlow")
if logger.handlers:
    return logger  # 已经配置过了
```

---

### L2. CLI 日志目录改为配置文件目录

**文件**: `multitaskflow/task_flow.py`，`_setup_logger` 方法

将 `"logs"` 改为相对于配置文件目录：
```python
log_dir = self.config_dir / "logs"
if not log_dir.exists():
    log_dir.mkdir(parents=True, exist_ok=True)

fh = logging.FileHandler(
    str(log_dir / f"taskflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    encoding='utf-8'
)
```

---

### L3. `check_new_tasks` 补充 env 参数

**文件**: `multitaskflow/task_flow.py`，`check_new_tasks` 方法（约第 695 行）

```python
task = Task(
    name=task_config['name'],
    command=task_config['command'],
    status=task_config.get('status', 'pending'),
    env=task_config.get('env', {})  # 添加这行
)
```

---

### L4. 恢复任务使用持久化的 start_time

**文件**: `multitaskflow/web/queue_manager.py`，`_restore_task_in_queue` 方法

```python
# 现状:
task.start_time = datetime.now()

# 改为使用保存的时间:
saved_start = self.running_tasks.get(task_id, {}).get('start_time')
if saved_start:
    try:
        task.start_time = datetime.fromisoformat(saved_start)
    except (ValueError, TypeError):
        task.start_time = datetime.now()
else:
    task.start_time = datetime.now()
```

---

### L5. 修复 `formatDuration` 零秒显示

**文件**: `multitaskflow/web/frontend/src/components/TaskTable.tsx`（约第 47 行）

```typescript
// 现状:
if (!seconds || seconds < 0) return '-';

// 改为:
if (seconds == null || seconds < 0) return '-';
```

---

### L6. AddQueueDialog 关闭时重置表单

**文件**: `multitaskflow/web/frontend/src/components/AddQueueDialog.tsx`

添加 `useEffect` 在弹窗打开时重置：
```typescript
useEffect(() => {
    if (isOpen) {
        setName('');
        setYamlPath('');
        setError('');
    }
}, [isOpen]);
```

---

### L7. 删除 LogStreamer 中的死代码

**文件**: `multitaskflow/web/ws.py`，`LogStreamer` 类

删除 `__init__` 中的：
```python
self.file_positions: Dict[str, int] = {}
self.line_buffers: Dict[str, str] = {}
```

以及 `disconnect` 方法中的：
```python
self.file_positions.pop(task_id, None)
self.line_buffers.pop(task_id, None)
```

---

### L8. Toolbar 按钮增加 loading 防重复

**文件**: `multitaskflow/web/frontend/src/components/Toolbar.tsx`

给各操作按钮加 `disabled` 状态，用一个 state 跟踪：
```typescript
const [loading, setLoading] = useState(false);

const handleCheckYaml = async () => {
    if (loading) return;
    setLoading(true);
    try {
        // 原有逻辑
    } finally {
        setLoading(false);
    }
};
```

对 handleReload、handleStopAll、handleClearHistory 同理。按钮传入 `disabled={loading}`。

---

### L9. 删除 XTerminal 未使用的 prop

**文件**: `multitaskflow/web/frontend/src/components/XTerminal.tsx`

从接口定义中删除 `onContentUpdate?: () => void`。

---

### L10. Header 版本号从 API 获取

**方案**: 后端已有 `/health` 端点，可扩展其返回值包含版本号：

**文件**: `multitaskflow/web/server.py`
```python
@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}
```

**文件**: `multitaskflow/web/frontend/src/components/Header.tsx`
- 从 `/health` 获取版本号展示，或者保持硬编码但更新为正确值也行（优先级低）。

---

### L11. 修复 `__init__.py` 版本注释

**文件**: `multitaskflow/__init__.py`

将文件头注释中的 `版本: 0.1.5` 改为 `版本: 1.0.5`。

---

### L12. 移除 LoginPage 误导性安全提示

**文件**: `multitaskflow/web/frontend/src/components/LoginPage.tsx`（约第 176 行）

删除或修改 "🔒 连接已加密保护" 这行文字。可改为中性描述如 "MultiTaskFlow Web UI"，或根据协议动态显示。

---

## 总计

| 优先级 | 数量 |
|--------|------|
| 🔴 High (必须修) | 5 |
| 🟡 Medium | 9 |
| 🟢 Low | 12 |
| **合计** | **26** |

建议按 H → M → L 顺序修复。Low 级别中 L7（删死代码）、L9（删未用 prop）、L11（改注释）改动最小可以顺手修。
