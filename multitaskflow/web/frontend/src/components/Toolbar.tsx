import { useTaskStore } from '../stores/taskStore';
import { api } from '../api';

interface ToolbarProps {
    onAddTask: () => void;
}

export function Toolbar({ onAddTask }: ToolbarProps) {
    const { queueStatus, startQueue, stopQueue, refreshTasks, refreshHistory, showToast } = useTaskStore();

    const handleCheckYaml = async () => {
        try {
            const result = await api.checkYaml();
            if (result.new_tasks?.length > 0) {
                if (confirm(`发现 ${result.new_tasks.length} 个新任务，加载？`)) {
                    await api.loadNewTasks();
                    showToast('已加载新任务', 'success');
                    await refreshTasks();
                }
            } else {
                showToast('无新任务', 'info');
            }
        } catch (e) {
            showToast('检查失败', 'error');
        }
    };

    const handleReload = async () => {
        if (!confirm('重新加载将清空队列，确定？')) return;
        try {
            await api.reloadTasks();
            showToast('已重新加载', 'success');
            await refreshTasks();
            await refreshHistory();
        } catch (e) {
            showToast('重新加载失败', 'error');
        }
    };

    const handleStopAll = async () => {
        if (!confirm('停止所有运行中的任务？')) return;
        try {
            await api.stopAll();
            showToast('已停止所有任务', 'success');
            await refreshTasks();
        } catch (e) {
            showToast('停止失败', 'error');
        }
    };

    const handleClearHistory = async () => {
        if (!confirm('清空执行历史？')) return;
        try {
            await api.clearHistory();
            showToast('历史已清空', 'success');
            await refreshHistory();
        } catch (e) {
            showToast('清空失败', 'error');
        }
    };

    return (
        <div className="flex items-center gap-2">
            {/* Queue control - primary action */}
            {!queueStatus.running ? (
                <button
                    onClick={startQueue}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                    </svg>
                    开始队列
                </button>
            ) : (
                <button
                    onClick={stopQueue}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium rounded-lg transition-colors"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" rx="1" />
                    </svg>
                    停止队列
                </button>
            )}

            {/* Add new task */}
            <button
                onClick={onAddTask}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                添加任务
            </button>

            {/* Check for new tasks */}
            <button
                onClick={handleCheckYaml}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/80 hover:bg-slate-600 text-slate-200 text-sm rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                检查任务
            </button>

            <div className="w-px h-5 bg-slate-600" />

            {/* Secondary actions */}
            <button
                onClick={handleReload}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/80 hover:bg-slate-600 text-slate-200 text-sm rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                重新加载
            </button>

            <button
                onClick={handleStopAll}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/80 hover:bg-red-600 text-slate-200 hover:text-white text-sm rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" />
                    <rect x="9" y="9" width="6" height="6" rx="0.5" fill="currentColor" />
                </svg>
                全部停止
            </button>

            <button
                onClick={handleClearHistory}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/80 hover:bg-slate-600 text-slate-200 text-sm rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                清空历史
            </button>
        </div>
    );
}
