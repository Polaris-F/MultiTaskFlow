// API client for MultiTaskFlow backend

const BASE_URL = '';

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

export const api = {
    async getTasks(): Promise<TasksResponse> {
        const res = await fetch(`${BASE_URL}/api/tasks`);
        return res.json();
    },

    async getHistory(): Promise<HistoryResponse> {
        const res = await fetch(`${BASE_URL}/api/history`);
        return res.json();
    },

    async addTask(task: { name: string; command: string; note?: string }) {
        const res = await fetch(`${BASE_URL}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        return res.json();
    },

    async updateTask(id: string, task: { name: string; command: string; note?: string }) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });
        return res.json();
    },

    async deleteTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}`, { method: 'DELETE' });
        return res.json();
    },

    async runTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}/run`, { method: 'POST' });
        return res.json();
    },

    async stopTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}/stop`, { method: 'POST' });
        return res.json();
    },

    async retryTask(id: string) {
        const res = await fetch(`${BASE_URL}/api/tasks/${id}/retry`, { method: 'POST' });
        return res.json();
    },

    async stopAll() {
        const res = await fetch(`${BASE_URL}/api/stop-all`, { method: 'POST' });
        return res.json();
    },

    async reloadTasks() {
        const res = await fetch(`${BASE_URL}/api/reload`, { method: 'POST' });
        return res.json();
    },

    async reorderTasks(order: string[]) {
        const res = await fetch(`${BASE_URL}/api/tasks/reorder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order })
        });
        return res.json();
    },

    async clearHistory() {
        const res = await fetch(`${BASE_URL}/api/history`, { method: 'DELETE' });
        return res.json();
    },

    async checkYaml() {
        const res = await fetch(`${BASE_URL}/api/check-yaml`);
        return res.json();
    },

    async loadNewTasks() {
        const res = await fetch(`${BASE_URL}/api/load-new-tasks`, { method: 'POST' });
        return res.json();
    },

    async loadSelectedTasks(tasks: { name: string; command: string; note?: string }[]) {
        const res = await fetch(`${BASE_URL}/api/load-selected-tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tasks })
        });
        return res.json();
    },

    async startQueue() {
        const res = await fetch(`${BASE_URL}/api/start-queue`, { method: 'POST' });
        return res.json();
    },

    async stopQueue() {
        const res = await fetch(`${BASE_URL}/api/stop-queue`, { method: 'POST' });
        return res.json();
    },

    async getQueueStatus(): Promise<QueueStatus> {
        const res = await fetch(`${BASE_URL}/api/queue-status`);
        return res.json();
    },

    async getTaskLog(taskId: string) {
        const res = await fetch(`${BASE_URL}/api/logs/${taskId}`);
        return res.json();
    },

    async getMainLog() {
        const res = await fetch(`${BASE_URL}/api/main-log`);
        return res.json();
    }
};
