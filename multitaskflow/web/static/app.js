// ============ State ============

const state = {
    tasks: [],
    runningTasks: [],
    pendingTasks: [],
    history: [],
    currentLogTask: null,
    logWebSocket: null,
    queueRunning: false,
    logPanelOpen: false
};

// ============ API ============

const API = {
    async getTasks() {
        const res = await fetch('/api/tasks');
        return res.json();
    },
    async getHistory() {
        const res = await fetch('/api/history');
        return res.json();
    },
    async addTask(task) {
        const res = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        return res.json();
    },
    async updateTask(id, task) {
        const res = await fetch(`/api/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        return res.json();
    },
    async deleteTask(id) {
        const res = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
        return res.json();
    },
    async runTask(id) {
        const res = await fetch(`/api/tasks/${id}/run`, { method: 'POST' });
        return res.json();
    },
    async stopTask(id) {
        const res = await fetch(`/api/tasks/${id}/stop`, { method: 'POST' });
        return res.json();
    },
    async stopAll() {
        const res = await fetch('/api/stop-all', { method: 'POST' });
        return res.json();
    },
    async reloadTasks() {
        const res = await fetch('/api/reload', { method: 'POST' });
        return res.json();
    },
    async reorderTasks(ids) {
        const res = await fetch('/api/tasks/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order: ids })
        });
        return res.json();
    },
    async clearHistory() {
        const res = await fetch('/api/history', { method: 'DELETE' });
        return res.json();
    },
    async checkYaml() {
        const res = await fetch('/api/check-yaml');
        return res.json();
    },
    async loadNewTasks() {
        const res = await fetch('/api/load-new-tasks', { method: 'POST' });
        return res.json();
    },
    async startQueue() {
        const res = await fetch('/api/start-queue', { method: 'POST' });
        return res.json();
    },
    async stopQueue() {
        const res = await fetch('/api/stop-queue', { method: 'POST' });
        return res.json();
    },
    async getQueueStatus() {
        const res = await fetch('/api/queue-status');
        return res.json();
    }
};

// ============ Utilities ============

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

// ============ Log Panel Show/Hide ============

function showLogPanel() {
    document.getElementById('log-panel').classList.remove('hidden');
    document.getElementById('resizer').classList.remove('hidden');
    state.logPanelOpen = true;
}

function hideLogPanel() {
    document.getElementById('log-panel').classList.add('hidden');
    document.getElementById('resizer').classList.add('hidden');
    state.logPanelOpen = false;
    state.currentLogTask = null;

    if (state.logWebSocket) {
        state.logWebSocket.close();
        state.logWebSocket = null;
    }
}

function initResizer() {
    const resizer = document.getElementById('resizer');
    const logPanel = document.getElementById('log-panel');
    let isResizing = false;

    resizer.addEventListener('mousedown', () => {
        isResizing = true;
        resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const container = document.getElementById('main-content');
        const containerRect = container.getBoundingClientRect();
        const newLogWidth = containerRect.right - e.clientX;

        const min = 250;
        const max = 700;
        const width = Math.max(min, Math.min(max, newLogWidth));

        logPanel.style.width = `${width}px`;
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

function initColumnResize() {
    const table = document.getElementById('task-table');
    const headers = table.querySelectorAll('th.resizable');

    headers.forEach(header => {
        let isResizing = false;
        let startX, startWidth;

        header.addEventListener('mousedown', (e) => {
            // Only start resize if clicking near the right edge
            const rect = header.getBoundingClientRect();
            if (e.clientX > rect.right - 10) {
                isResizing = true;
                startX = e.clientX;
                startWidth = header.offsetWidth;
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const diff = e.clientX - startX;
            const newWidth = Math.max(30, startWidth + diff);
            header.style.width = `${newWidth}px`;
            header.style.minWidth = `${newWidth}px`;
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    });
}

// ============ Data Loading ============

async function refreshTasks() {
    try {
        const data = await API.getTasks();
        state.pendingTasks = data.pending || [];
        state.runningTasks = data.running || [];
        state.tasks = [...state.runningTasks, ...state.pendingTasks];

        renderTaskTable();
        updateQueueStatus();
    } catch (e) {
        console.error('刷新失败:', e);
    }
}

async function refreshHistory() {
    try {
        const data = await API.getHistory();
        state.history = data.history || [];
        renderTaskTable();
    } catch (e) {
        console.error('刷新历史失败:', e);
    }
}

async function updateQueueStatus() {
    try {
        const data = await API.getQueueStatus();
        state.queueRunning = data.running;

        const statusBadge = document.getElementById('queue-status');
        const startBtn = document.getElementById('btn-start-queue');
        const stopBtn = document.getElementById('btn-stop-queue');

        if (data.running) {
            statusBadge.textContent = '队列运行中';
            statusBadge.classList.add('running');
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-flex';
        } else if (state.runningTasks.length > 0) {
            statusBadge.textContent = `运行 ${state.runningTasks.length}`;
            statusBadge.classList.add('running');
            startBtn.style.display = 'inline-flex';
            stopBtn.style.display = 'none';
        } else {
            statusBadge.textContent = '空闲';
            statusBadge.classList.remove('running');
            startBtn.style.display = 'inline-flex';
            stopBtn.style.display = 'none';
        }
    } catch (e) { }
}

// ============ Task Table ============

function getStatusIcon(status) {
    switch (status) {
        case 'running': return '<span class="status-icon status-running" title="运行中">⚡</span>';
        case 'pending': return '<span class="status-icon status-pending" title="等待中">⏳</span>';
        case 'completed': return '<span class="status-icon status-completed" title="完成">✅</span>';
        case 'failed': return '<span class="status-icon status-failed" title="失败">❌</span>';
        default: return '<span class="status-icon" title="未知">◯</span>';
    }
}

function renderTaskTable() {
    const tbody = document.getElementById('task-table-body');
    const noTasks = document.getElementById('no-tasks');

    // 合并所有任务，按原始顺序排列（用 task_order 字段或保持原有顺序）
    // 创建 ID 到任务的映射
    const taskMap = new Map();

    // 优先级：running > pending > history
    state.runningTasks.forEach(t => taskMap.set(t.id, t));
    state.pendingTasks.forEach(t => { if (!taskMap.has(t.id)) taskMap.set(t.id, t); });
    state.history.slice(0, 20).forEach(t => { if (!taskMap.has(t.id)) taskMap.set(t.id, t); });

    // 按原始顺序构建任务列表：running + pending 的顺序在前，history 在后但按时间倒序
    const activeTasks = [...state.runningTasks, ...state.pendingTasks];
    const historyTasks = state.history.slice(0, 15).filter(t => !taskMap.has(t.id) ||
        (taskMap.get(t.id).status === 'completed' || taskMap.get(t.id).status === 'failed'));

    const allTasks = [...activeTasks, ...historyTasks];

    if (allTasks.length === 0) {
        tbody.innerHTML = '';
        noTasks.style.display = 'block';
        return;
    }

    noTasks.style.display = 'none';

    tbody.innerHTML = allTasks.map((task, index) => {
        const isRunning = task.status === 'running';
        const isPending = task.status === 'pending';
        const isCompleted = task.status === 'completed';
        const isFailed = task.status === 'failed';
        const isHistory = isCompleted || isFailed;
        const hasLog = isRunning || task.log_file;

        const duration = task.duration ? formatDuration(task.duration) :
            (task.start_time && isRunning ? '...' : '-');

        const rowClass = isRunning ? 'row-running' :
            isCompleted ? 'row-completed' :
                isFailed ? 'row-failed' : '';

        // Build action buttons based on task status
        let actions = [];

        if (isPending) {
            actions.push(`<button class="btn btn-sm btn-icon" onclick="moveTask('${task.id}', -1)" title="上移">▲</button>`);
            actions.push(`<button class="btn btn-sm btn-icon" onclick="moveTask('${task.id}', 1)" title="下移">▼</button>`);
            actions.push(`<button class="btn btn-sm btn-icon btn-success" onclick="runTask('${task.id}')" title="运行">▶</button>`);
            actions.push(`<button class="btn btn-sm btn-icon" onclick="editTask('${task.id}')" title="编辑">✏️</button>`);
            actions.push(`<button class="btn btn-sm btn-icon btn-danger" onclick="deleteTask('${task.id}')" title="删除">🗑</button>`);
        }

        if (isRunning) {
            actions.push(`<button class="btn btn-sm btn-icon btn-warning" onclick="stopTask('${task.id}')" title="停止">⏹</button>`);
        }

        if (hasLog) {
            actions.push(`<button class="btn btn-sm btn-icon btn-primary" onclick="viewLog('${task.id}')" title="查看日志">📜</button>`);
        }

        return `
            <tr data-id="${task.id}" class="${rowClass}">
                <td class="col-order">${index + 1}</td>
                <td class="col-status">${getStatusIcon(task.status)}</td>
                <td class="col-name" title="${escapeHtml(task.name)}">${escapeHtml(task.name)}</td>
                <td class="col-command"><span class="command-text" title="${escapeHtml(task.command)}">${escapeHtml(task.command)}</span></td>
                <td class="col-duration">${duration}</td>
                <td class="col-actions"><div class="action-btns">${actions.join('')}</div></td>
            </tr>
        `;
    }).join('');
}

// ============ Task Actions ============

async function runTask(id) {
    try {
        const result = await API.runTask(id);
        showToast(result.success ? '已启动' : (result.message || '失败'), result.success ? 'success' : 'error');
        await refreshTasks();
    } catch (e) {
        showToast('失败: ' + e.message, 'error');
    }
}

async function stopTask(id) {
    try {
        await API.stopTask(id);
        showToast('已停止', 'success');
        await refreshTasks();
    } catch (e) {
        showToast('失败', 'error');
    }
}

async function deleteTask(id) {
    if (!confirm('确定删除此任务？')) return;
    try {
        const result = await API.deleteTask(id);
        if (result.success) {
            showToast('已删除', 'success');
            await refreshTasks();
            await refreshHistory();
        } else {
            showToast(result.message || '删除失败', 'error');
        }
    } catch (e) {
        showToast('删除失败: ' + e.message, 'error');
    }
}

async function moveTask(id, direction) {
    // Only pending tasks can be reordered
    const pendingIds = state.pendingTasks.map(t => t.id);
    const index = pendingIds.indexOf(id);

    if (index === -1) {
        showToast('只能调整待执行任务的顺序', 'error');
        return;
    }

    const newIndex = index + direction;

    if (newIndex < 0 || newIndex >= pendingIds.length) {
        return; // Out of bounds, do nothing
    }

    // Swap
    [pendingIds[index], pendingIds[newIndex]] = [pendingIds[newIndex], pendingIds[index]];

    try {
        const result = await API.reorderTasks(pendingIds);
        if (result.success) {
            await refreshTasks();
        } else {
            showToast(result.message || '排序失败', 'error');
        }
    } catch (e) {
        showToast('排序失败: ' + e.message, 'error');
    }
}

// ============ Log Viewing ============

function viewLog(taskId) {
    state.currentLogTask = taskId;
    showLogPanel();

    const logContent = document.getElementById('log-content');
    const logFilePath = document.getElementById('log-file-path');
    const logTitle = document.getElementById('log-title');
    const copyWinBtn = document.getElementById('btn-copy-win');
    const copyLinuxBtn = document.getElementById('btn-copy-linux');

    logContent.innerHTML = '<p class="log-placeholder">加载中...</p>';

    if (state.logWebSocket) {
        state.logWebSocket.close();
        state.logWebSocket = null;
    }

    // Main log
    if (taskId === 'main') {
        logTitle.textContent = '📊 主进程';
        loadMainLog();
        return;
    }

    // Find task
    const task = state.runningTasks.find(t => t.id === taskId) ||
        state.pendingTasks.find(t => t.id === taskId) ||
        state.history.find(t => t.id === taskId);

    if (!task) {
        logContent.innerHTML = '<p class="log-placeholder">任务不存在</p>';
        return;
    }

    logTitle.textContent = `📜 ${task.name}`;

    if (task.log_file) {
        logFilePath.style.display = 'block';
        logFilePath.innerHTML = `<code>${escapeHtml(task.log_file)}</code>`;

        copyWinBtn.style.display = 'inline-block';
        copyLinuxBtn.style.display = 'inline-block';

        copyWinBtn.onclick = () => {
            navigator.clipboard.writeText(`Get-Content -Path "${task.log_file}" -Wait -Tail 50`)
                .then(() => showToast('已复制', 'success'));
        };

        copyLinuxBtn.onclick = () => {
            navigator.clipboard.writeText(`tail -f "${task.log_file}"`)
                .then(() => showToast('已复制', 'success'));
        };
    } else {
        logFilePath.style.display = 'none';
        copyWinBtn.style.display = 'none';
        copyLinuxBtn.style.display = 'none';
    }

    // Running: WebSocket
    if (task.status === 'running') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs/${taskId}`;

        try {
            state.logWebSocket = new WebSocket(wsUrl);

            state.logWebSocket.onopen = () => { logContent.innerHTML = ''; };

            state.logWebSocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    const span = document.createElement('span');
                    span.textContent = data.content;
                    logContent.appendChild(span);
                    logContent.scrollTop = logContent.scrollHeight;
                } else if (data.type === 'end') {
                    const div = document.createElement('div');
                    div.style.cssText = 'margin-top: 8px; padding: 6px; background: var(--bg-secondary); border-radius: 4px; text-align: center; font-size: 11px;';
                    div.innerHTML = `✅ ${data.message}`;
                    logContent.appendChild(div);
                    refreshTasks();
                    refreshHistory();
                }
            };

            state.logWebSocket.onerror = () => {
                logContent.innerHTML = '<p class="log-placeholder" style="color: var(--accent-danger);">连接失败</p>';
            };
        } catch (e) {
            logContent.innerHTML = `<p class="log-placeholder">${e.message}</p>`;
        }
    } else {
        loadTaskLog(taskId);
    }
}

async function loadTaskLog(taskId) {
    const logContent = document.getElementById('log-content');
    try {
        const res = await fetch(`/api/logs/${taskId}`);
        const data = await res.json();

        if (data.success) {
            logContent.innerHTML = '';
            const pre = document.createElement('pre');
            pre.style.cssText = 'margin: 0; white-space: pre-wrap;';
            pre.textContent = data.content || '日志为空';
            logContent.appendChild(pre);
            logContent.scrollTop = logContent.scrollHeight;
        } else {
            logContent.innerHTML = `<p class="log-placeholder">${data.detail || '加载失败'}</p>`;
        }
    } catch (e) {
        logContent.innerHTML = `<p class="log-placeholder">${e.message}</p>`;
    }
}

async function loadMainLog() {
    const logContent = document.getElementById('log-content');
    const logFilePath = document.getElementById('log-file-path');
    const copyWinBtn = document.getElementById('btn-copy-win');
    const copyLinuxBtn = document.getElementById('btn-copy-linux');

    try {
        const res = await fetch('/api/main-log');
        const data = await res.json();

        if (data.success) {
            logFilePath.style.display = 'block';
            logFilePath.innerHTML = `<code>${escapeHtml(data.log_file)}</code>`;

            copyWinBtn.style.display = 'inline-block';
            copyLinuxBtn.style.display = 'inline-block';

            copyWinBtn.onclick = () => {
                navigator.clipboard.writeText(`Get-Content -Path "${data.log_file}" -Wait -Tail 50`)
                    .then(() => showToast('已复制', 'success'));
            };
            copyLinuxBtn.onclick = () => {
                navigator.clipboard.writeText(`tail -f "${data.log_file}"`)
                    .then(() => showToast('已复制', 'success'));
            };

            logContent.innerHTML = '';
            const pre = document.createElement('pre');
            pre.style.cssText = 'margin: 0; white-space: pre-wrap;';
            pre.textContent = data.content || '日志为空';
            logContent.appendChild(pre);
            logContent.scrollTop = logContent.scrollHeight;

            if (state.currentLogTask === 'main') {
                setTimeout(loadMainLog, 3000);
            }
        }
    } catch (e) {
        logContent.innerHTML = `<p class="log-placeholder">${e.message}</p>`;
    }
}

// ============ Modal ============

let editingTaskId = null;

function openModal(title = '添加任务') {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('task-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('task-modal').classList.add('hidden');
    document.getElementById('task-form').reset();
    editingTaskId = null;
}

function editTask(id) {
    const task = state.tasks.find(t => t.id === id);
    if (!task) return;

    editingTaskId = id;
    document.getElementById('task-name').value = task.name;
    document.getElementById('task-command').value = task.command;
    openModal('编辑任务');
}

async function handleFormSubmit(e) {
    e.preventDefault();

    const taskData = {
        name: document.getElementById('task-name').value.trim(),
        command: document.getElementById('task-command').value.trim()
    };

    try {
        if (editingTaskId) {
            await API.updateTask(editingTaskId, taskData);
        } else {
            await API.addTask(taskData);
        }
        showToast('已保存', 'success');
        closeModal();
        await refreshTasks();
    } catch (e) {
        showToast('失败', 'error');
    }
}

// ============ Event Bindings ============

document.addEventListener('DOMContentLoaded', () => {
    refreshTasks();
    refreshHistory();

    setInterval(() => {
        refreshTasks();
        refreshHistory();
    }, 5000);

    initResizer();
    initColumnResize();

    // Toolbar buttons
    document.getElementById('btn-add-task').addEventListener('click', () => openModal());

    document.getElementById('btn-start-queue').addEventListener('click', async () => {
        try {
            const result = await API.startQueue();
            showToast(result.message, result.success ? 'success' : 'error');
            await updateQueueStatus();
            await refreshTasks();
        } catch (e) {
            showToast('失败', 'error');
        }
    });

    document.getElementById('btn-stop-queue').addEventListener('click', async () => {
        try {
            await API.stopQueue();
            showToast('队列将停止', 'success');
            await updateQueueStatus();
        } catch (e) {
            showToast('失败', 'error');
        }
    });

    document.getElementById('btn-check-yaml').addEventListener('click', async () => {
        try {
            const result = await API.checkYaml();
            if (result.new_tasks?.length > 0) {
                if (confirm(`发现 ${result.new_tasks.length} 个新任务，加载？`)) {
                    await API.loadNewTasks();
                    showToast('已加载', 'success');
                    await refreshTasks();
                }
            } else {
                showToast('无新任务', 'info');
            }
        } catch (e) {
            showToast('检查失败', 'error');
        }
    });

    document.getElementById('btn-reload').addEventListener('click', async () => {
        if (!confirm('重新加载？')) return;
        try {
            await API.reloadTasks();
            showToast('已重载', 'success');
            await refreshTasks();
            await refreshHistory();
        } catch (e) {
            showToast('失败', 'error');
        }
    });

    document.getElementById('btn-stop-all').addEventListener('click', async () => {
        if (!confirm('停止所有？')) return;
        try {
            await API.stopAll();
            showToast('已停止', 'success');
            await refreshTasks();
        } catch (e) {
            showToast('失败', 'error');
        }
    });

    document.getElementById('btn-clear-history').addEventListener('click', async () => {
        if (!confirm('清空历史？')) return;
        try {
            await API.clearHistory();
            showToast('已清空', 'success');
            await refreshHistory();
        } catch (e) {
            showToast('失败', 'error');
        }
    });

    document.getElementById('btn-close-log').addEventListener('click', hideLogPanel);

    document.getElementById('task-form').addEventListener('submit', handleFormSubmit);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            if (state.logPanelOpen) hideLogPanel();
        }
    });
});
