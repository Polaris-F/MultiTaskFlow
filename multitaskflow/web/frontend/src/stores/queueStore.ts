import { create } from 'zustand';

export interface QueueInfo {
    id: string;
    name: string;
    yaml_path: string;
    created_at: string;
    status?: {
        queue_running: boolean;
        pending_count: number;
        running_count: number;
    };
}

interface QueueState {
    // Queue list
    queues: QueueInfo[];
    currentQueueId: string | null;
    isLoading: boolean;

    // Actions
    fetchQueues: () => Promise<void>;
    addQueue: (name: string, yamlPath: string) => Promise<boolean>;
    removeQueue: (queueId: string) => Promise<boolean>;
    setCurrentQueue: (queueId: string) => void;

    // GPU usage
    globalGpuUsage: Record<number, string>;
    fetchGlobalGpuUsage: () => Promise<void>;
}

export const useQueueStore = create<QueueState>((set, get) => ({
    queues: [],
    currentQueueId: null,
    isLoading: false,
    globalGpuUsage: {},

    fetchQueues: async () => {
        set({ isLoading: true });
        try {
            const res = await fetch('/api/queues');
            const data = await res.json();
            const queues = data.queues || [];
            const backendCurrentQueueId = data.current_queue_id;

            set({ queues, isLoading: false });

            // Sync current queue ID from backend if available
            if (backendCurrentQueueId && queues.some((q: { id: string }) => q.id === backendCurrentQueueId)) {
                set({ currentQueueId: backendCurrentQueueId });
            } else if (!get().currentQueueId && queues.length > 0) {
                // Auto-select first queue if none selected (also notify backend)
                get().setCurrentQueue(queues[0].id);
            }
        } catch (e) {
            console.error('Failed to fetch queues:', e);
            set({ isLoading: false });
        }
    },

    addQueue: async (name: string, yamlPath: string) => {
        try {
            const res = await fetch('/api/queues', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, yaml_path: yamlPath }),
            });
            const data = await res.json();

            if (data.success) {
                await get().fetchQueues();
                // Switch to new queue
                if (data.queue?.id) {
                    set({ currentQueueId: data.queue.id });
                }
                return true;
            }
            return false;
        } catch (e) {
            console.error('Failed to add queue:', e);
            return false;
        }
    },

    removeQueue: async (queueId: string) => {
        try {
            const res = await fetch(`/api/queues/${queueId}`, { method: 'DELETE' });
            const data = await res.json();

            if (data.success) {
                await get().fetchQueues();

                // If removed current queue, switch to first available
                if (get().currentQueueId === queueId) {
                    const queues = get().queues;
                    set({ currentQueueId: queues.length > 0 ? queues[0].id : null });
                }
                return true;
            }
            return false;
        } catch (e) {
            console.error('Failed to remove queue:', e);
            return false;
        }
    },

    setCurrentQueue: async (queueId: string) => {
        // Notify backend of queue switch
        try {
            await fetch(`/api/queues/${queueId}/select`, { method: 'POST' });
        } catch (e) {
            console.error('Failed to select queue:', e);
        }
        set({ currentQueueId: queueId });
    },

    fetchGlobalGpuUsage: async () => {
        try {
            const res = await fetch('/api/global/gpu-usage');
            const data = await res.json();
            set({ globalGpuUsage: data.gpu_usage || {} });
        } catch (e) {
            console.error('Failed to fetch GPU usage:', e);
        }
    },
}));
