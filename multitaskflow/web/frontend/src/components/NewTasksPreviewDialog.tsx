import { useState } from 'react';

interface NewTask {
    name: string;
    command: string;
    note?: string;
}

interface NewTasksPreviewDialogProps {
    tasks: NewTask[];
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
}

export function NewTasksPreviewDialog({ tasks, isOpen, onClose, onConfirm }: NewTasksPreviewDialogProps) {
    const [loading, setLoading] = useState(false);

    if (!isOpen) return null;

    const handleConfirm = async () => {
        setLoading(true);
        await onConfirm();
        setLoading(false);
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden border border-slate-700"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                        📋 发现新任务
                        <span className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded-full">
                            {tasks.length}
                        </span>
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content - 任务列表预览 */}
                <div className="p-5 max-h-[60vh] overflow-y-auto">
                    <p className="text-slate-400 text-sm mb-4">
                        以下任务将被添加到队列中：
                    </p>

                    <div className="space-y-3">
                        {tasks.map((task, index) => (
                            <div
                                key={index}
                                className="bg-slate-900/50 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                        {/* 序号和名称 */}
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-slate-700 text-slate-300 text-xs rounded-full">
                                                {index + 1}
                                            </span>
                                            <span className="text-slate-100 font-medium truncate">
                                                {task.name}
                                            </span>
                                        </div>

                                        {/* 命令 */}
                                        <div className="pl-8">
                                            <code className="text-xs text-emerald-400 font-mono break-all line-clamp-2">
                                                {task.command}
                                            </code>
                                        </div>

                                        {/* 备注 */}
                                        {task.note && (
                                            <div className="pl-8 mt-2">
                                                <span className="text-xs text-slate-500">{task.note}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div className="flex justify-between items-center px-5 py-4 border-t border-slate-700 bg-slate-800/50">
                    <span className="text-sm text-slate-400">
                        共 {tasks.length} 个任务
                    </span>
                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
                            disabled={loading}
                        >
                            取消
                        </button>
                        <button
                            onClick={handleConfirm}
                            disabled={loading}
                            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            {loading ? (
                                <>
                                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    加载中...
                                </>
                            ) : (
                                <>
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                                    </svg>
                                    加载任务
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
