import { useState } from 'react';
import { useQueueStore } from '../stores/queueStore';
import { useTaskStore } from '../stores/taskStore';

interface QueueTabsProps {
    onAddQueue: () => void;
}

export function QueueTabs({ onAddQueue }: QueueTabsProps) {
    const { queues, currentQueueId, setCurrentQueue, removeQueue } = useQueueStore();
    const { showToast } = useTaskStore();
    const [contextMenu, setContextMenu] = useState<{ x: number; y: number; queueId: string } | null>(null);

    const handleTabClick = (queueId: string) => {
        setCurrentQueue(queueId);
    };

    const handleContextMenu = (e: React.MouseEvent, queueId: string) => {
        e.preventDefault();
        setContextMenu({ x: e.clientX, y: e.clientY, queueId });
    };

    const handleRemoveQueue = async (queueId: string) => {
        setContextMenu(null);
        if (confirm('确定移除此队列？（不会删除文件）')) {
            const success = await removeQueue(queueId);
            if (success) {
                showToast('队列已移除', 'success');
            } else {
                showToast('移除失败', 'error');
            }
        }
    };

    const closeContextMenu = () => setContextMenu(null);

    return (
        <>
            <div className="flex items-center gap-1 bg-slate-900/50 rounded-lg p-1">
                {queues.map((queue) => (
                    <button
                        key={queue.id}
                        onClick={() => handleTabClick(queue.id)}
                        onContextMenu={(e) => handleContextMenu(e, queue.id)}
                        className={`
                            flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all
                            ${currentQueueId === queue.id
                                ? 'bg-blue-600 text-white shadow-lg'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                            }
                        `}
                        title={queue.yaml_path}
                    >
                        {/* Status indicator */}
                        <span className={`w-2 h-2 rounded-full ${queue.status?.running_count ?? 0 > 0
                            ? 'bg-emerald-400 animate-pulse'
                            : queue.status?.queue_running
                                ? 'bg-amber-400'
                                : 'bg-slate-500'
                            }`} />

                        {/* Queue name */}
                        <span className="max-w-[120px] truncate">{queue.name}</span>

                        {/* Task counts */}
                        {(queue.status?.pending_count ?? 0) + (queue.status?.running_count ?? 0) > 0 && (
                            <span className="text-xs opacity-70">
                                {queue.status?.running_count ?? 0}/{queue.status?.pending_count ?? 0}
                            </span>
                        )}
                    </button>
                ))}

                {/* Add queue button */}
                <button
                    onClick={onAddQueue}
                    className="flex items-center gap-1 px-2 py-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md transition-all"
                    title="添加任务队列"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                    </svg>
                    {queues.length === 0 && <span className="text-sm">添加队列</span>}
                </button>
            </div>

            {/* Context menu */}
            {contextMenu && (
                <>
                    <div className="fixed inset-0 z-40" onClick={closeContextMenu} />
                    <div
                        className="fixed z-50 bg-slate-800 rounded-lg shadow-xl border border-slate-700 py-1 min-w-[120px]"
                        style={{ left: contextMenu.x, top: contextMenu.y }}
                    >
                        <button
                            onClick={() => handleRemoveQueue(contextMenu.queueId)}
                            className="w-full px-3 py-1.5 text-left text-sm text-red-400 hover:bg-slate-700 flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            移除队列
                        </button>
                    </div>
                </>
            )}
        </>
    );
}
