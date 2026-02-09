// API client for MultiTaskFlow backend

const BASE_URL = '';

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

export interface Task {
    id: string;
    name: string;
    command: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
    gpu?: string;
    start_time?: string;
    end_time?: string;
    duration?: number;
    log_file?: string;
    error_message?: string;
    can_run?: boolean;
    conflict_message?: string;
    note?: string;
}

export interface TasksResponse {
    pending: Task[];
    running: Task[];
}

export interface HistoryResponse {
    history: Task[];
}

export interface QueueStatus {
    running: boolean;
    current_task?: string;
}

export interface HealthResponse {
    status: string;
    version?: string;
}

export const api = {
    async getTasks(): Promise<TasksResponse> {
        const res = await fetch(`${BASE_URL}/api/tasks`);
        return handleResponse<TasksResponse>(res);
    },

    async getHistory(): Promise<HistoryResponse> {
        const res = await fetch(`${BASE_URL}/api/history`);
        return handleResponse<HistoryResponse>(res);
    },

    async addTask(task: { name: string; command: string; note?: string }) {
        const res = await fetch(`${BASE_URL}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        return handleResponse<any>(res);
    },

    async updateTask(id: string, task: { name: string; command: string; note?: string }) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        return handleResponse<any>(res);
    },

    async deleteTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}`, { method: 'DELETE' });
        return handleResponse<any>(res);
    },

    async runTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}/run`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async stopTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}/stop`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async retryTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}/retry`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async stopAll() {
        const res = await fetch(`${BASE_URL}/api/stop-all`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async reloadTasks() {
        const res = await fetch(`${BASE_URL}/api/reload`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async reorderTasks(order: string[]) {
        const res = await fetch(`${BASE_URL}/api/tasks/reorder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order })
        });
        return handleResponse<any>(res);
    },

    async clearHistory() {
        const res = await fetch(`${BASE_URL}/api/history`, { method: 'DELETE' });
        return handleResponse<any>(res);
    },

    async checkYaml() {
        const res = await fetch(`${BASE_URL}/api/check-yaml`);
        return handleResponse<any>(res);
    },

    async loadNewTasks() {
        const res = await fetch(`${BASE_URL}/api/load-new-tasks`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async loadSelectedTasks(tasks: { name: string; command: string; note?: string }[]) {
        const res = await fetch(`${BASE_URL}/api/load-selected-tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tasks })
        });
        return handleResponse<any>(res);
    },

    async startQueue() {
        const res = await fetch(`${BASE_URL}/api/start-queue`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async stopQueue() {
        const res = await fetch(`${BASE_URL}/api/stop-queue`, { method: 'POST' });
        return handleResponse<any>(res);
    },

    async getQueueStatus(): Promise<QueueStatus> {
        const res = await fetch(`${BASE_URL}/api/queue-status`);
        return handleResponse<QueueStatus>(res);
    },

    async getTaskLog(taskId: string) {
        const res = await fetch(`${BASE_URL}/api/logs/${taskId}`);
        return handleResponse<any>(res);
    },

    async getMainLog() {
        const res = await fetch(`${BASE_URL}/api/main-log`);
        return handleResponse<any>(res);
    },

    async getHealth(): Promise<HealthResponse> {
        const res = await fetch(`${BASE_URL}/health`);
        return handleResponse<HealthResponse>(res);
    },
};
