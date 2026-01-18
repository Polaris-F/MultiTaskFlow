import { create } from 'zustand';
import { api, type Task, type QueueStatus } from '../api';

interface TaskStore {
    // State
    pendingTasks: Task[];
    runningTasks: Task[];
    history: Task[];
    queueStatus: QueueStatus;
    currentLogTask: string | null;
    logContent: string;
    logPanelOpen: boolean;
    toasts: { id: number; message: string; type: 'success' | 'error' | 'info' }[];
    // Stable task order: array of task IDs in display order
    // This order NEVER changes except when user manually reorders or tasks are added/deleted
    taskOrder: string[];
    // Set of known task IDs (to detect truly new tasks vs transitioning tasks)
    knownTaskIds: Set<string>;

    // Actions
    refreshTasks: () => Promise<void>;
    refreshHistory: () => Promise<void>;
    refreshQueueStatus: () => Promise<void>;
    runTask: (id: string) => Promise<void>;
    stopTask: (id: string) => Promise<void>;
    deleteTask: (id: string) => Promise<void>;
    moveTask: (id: string, direction: number) => Promise<void>;
    startQueue: () => Promise<void>;
    stopQueue: () => Promise<void>;
    setCurrentLogTask: (id: string | null) => void;
    setLogContent: (content: string) => void;
    appendLogContent: (content: string) => void;
    setLogPanelOpen: (open: boolean) => void;
    showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
    removeToast: (id: number) => void;
    // Get all tasks in stable order
    getAllTasksOrdered: () => Task[];
}

let toastId = 0;

export const useTaskStore = create<TaskStore>((set, get) => ({
    // Initial state
    pendingTasks: [],
    runningTasks: [],
    history: [],
    queueStatus: { running: false },
    currentLogTask: null,
    logContent: '',
    logPanelOpen: false,
    toasts: [],
    taskOrder: [],
    knownTaskIds: new Set(),

    // Actions
    refreshTasks: async () => {
        try {
            const data = await api.getTasks();
            const pending = data.pending || [];
            const running = data.running || [];

            const { taskOrder, knownTaskIds, history } = get();

            // Collect all current task IDs
            const allTasks = [...running, ...pending, ...history];

            // Find truly new tasks (never seen before)
            const newTaskIds: string[] = [];
            allTasks.forEach(t => {
                if (!knownTaskIds.has(t.id)) {
                    newTaskIds.push(t.id);
                }
            });

            // Update known task IDs
            const updatedKnownIds = new Set(knownTaskIds);
            newTaskIds.forEach(id => updatedKnownIds.add(id));

            // Update task order: keep existing order, add new tasks at end
            // Do NOT remove tasks from order even if they temporarily disappear
            const newOrder = [...taskOrder];
            newTaskIds.forEach(id => {
                if (!newOrder.includes(id)) {
                    newOrder.push(id);
                }
            });

            set({
                pendingTasks: pending,
                runningTasks: running,
                taskOrder: newOrder,
                knownTaskIds: updatedKnownIds
            });
        } catch (e) {
            console.error('Failed to fetch tasks:', e);
        }
    },

    refreshHistory: async () => {
        try {
            const data = await api.getHistory();
            const historyData = data.history || [];

            const { taskOrder, knownTaskIds, runningTasks, pendingTasks } = get();

            // Collect all current task IDs
            const allTasks = [...runningTasks, ...pendingTasks, ...historyData];

            // Find truly new tasks (never seen before)
            const newTaskIds: string[] = [];
            allTasks.forEach(t => {
                if (!knownTaskIds.has(t.id)) {
                    newTaskIds.push(t.id);
                }
            });

            // Update known task IDs
            const updatedKnownIds = new Set(knownTaskIds);
            newTaskIds.forEach(id => updatedKnownIds.add(id));

            // Update task order: keep existing order, add new tasks at end
            const newOrder = [...taskOrder];
            newTaskIds.forEach(id => {
                if (!newOrder.includes(id)) {
                    newOrder.push(id);
                }
            });

            set({
                history: historyData,
                taskOrder: newOrder,
                knownTaskIds: updatedKnownIds
            });
        } catch (e) {
            console.error('Failed to fetch history:', e);
        }
    },

    refreshQueueStatus: async () => {
        try {
            const status = await api.getQueueStatus();
            set({ queueStatus: status });
        } catch (e) {
            console.error('Failed to fetch queue status:', e);
        }
    },

    runTask: async (id: string) => {
        try {
            const result = await api.runTask(id);
            if (result.success) {
                get().showToast('任务已启动', 'success');
                await get().refreshTasks();
            } else {
                get().showToast(result.message || '启动失败', 'error');
            }
        } catch (e) {
            get().showToast('启动失败', 'error');
        }
    },

    stopTask: async (id: string) => {
        try {
            await api.stopTask(id);
            get().showToast('已停止', 'success');
            await get().refreshTasks();
        } catch (e) {
            get().showToast('停止失败', 'error');
        }
    },

    deleteTask: async (id: string) => {
        try {
            const result = await api.deleteTask(id);
            if (result.success) {
                // Remove from taskOrder and knownTaskIds when explicitly deleted
                const { taskOrder, knownTaskIds } = get();
                const newOrder = taskOrder.filter(tid => tid !== id);
                const newKnownIds = new Set(knownTaskIds);
                newKnownIds.delete(id);

                set({ taskOrder: newOrder, knownTaskIds: newKnownIds });

                get().showToast('已删除', 'success');
                await get().refreshTasks();
                await get().refreshHistory();
            } else {
                get().showToast(result.message || '删除失败', 'error');
            }
        } catch (e) {
            get().showToast('删除失败', 'error');
        }
    },

    moveTask: async (id: string, direction: number) => {
        const { pendingTasks, taskOrder } = get();
        const pendingIds = pendingTasks.map(t => t.id);
        const index = pendingIds.indexOf(id);
        const newIndex = index + direction;

        if (newIndex < 0 || newIndex >= pendingIds.length) return;

        // Swap in pending list for API call
        [pendingIds[index], pendingIds[newIndex]] = [pendingIds[newIndex], pendingIds[index]];

        // Also swap in taskOrder to maintain consistency
        const orderIndex = taskOrder.indexOf(id);
        const swapId = pendingTasks[newIndex].id; // The task we're swapping with
        const swapOrderIndex = taskOrder.indexOf(swapId);

        if (orderIndex !== -1 && swapOrderIndex !== -1) {
            const newTaskOrder = [...taskOrder];
            [newTaskOrder[orderIndex], newTaskOrder[swapOrderIndex]] = [newTaskOrder[swapOrderIndex], newTaskOrder[orderIndex]];
            set({ taskOrder: newTaskOrder });
        }

        try {
            const result = await api.reorderTasks(pendingIds);
            if (result.success) {
                await get().refreshTasks();
            } else {
                get().showToast('排序失败', 'error');
            }
        } catch (e) {
            get().showToast('排序失败', 'error');
        }
    },

    startQueue: async () => {
        try {
            const result = await api.startQueue();
            get().showToast(result.message, result.success ? 'success' : 'error');
            await get().refreshQueueStatus();
            await get().refreshTasks();
        } catch (e) {
            get().showToast('启动队列失败', 'error');
        }
    },

    stopQueue: async () => {
        try {
            await api.stopQueue();
            get().showToast('队列将停止', 'success');
            await get().refreshQueueStatus();
        } catch (e) {
            get().showToast('停止队列失败', 'error');
        }
    },

    setCurrentLogTask: (id) => set({ currentLogTask: id }),
    setLogContent: (content) => set({ logContent: content }),
    appendLogContent: (content) => set((s) => ({ logContent: s.logContent + content })),
    setLogPanelOpen: (open) => set({ logPanelOpen: open }),

    showToast: (message, type = 'success') => {
        const id = ++toastId;
        set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
        setTimeout(() => get().removeToast(id), 3000);
    },

    removeToast: (id) => set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) })),

    // Get all tasks in stable order
    getAllTasksOrdered: () => {
        const { runningTasks, pendingTasks, history, taskOrder } = get();
        const taskMap = new Map<string, Task>();

        // Build a map of all tasks
        [...runningTasks, ...pendingTasks, ...history].forEach(t => {
            taskMap.set(t.id, t);
        });

        // Return tasks in stable order (only those that currently exist)
        return taskOrder
            .filter(id => taskMap.has(id))
            .map(id => taskMap.get(id)!);
    }
}));
