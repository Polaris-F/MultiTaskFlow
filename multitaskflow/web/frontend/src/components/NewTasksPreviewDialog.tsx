import { useState, useEffect } from 'react';

interface NewTask {
    name: string;
    command: string;
    note?: string;
    valid?: boolean;
    error?: string;
}

interface NewTasksPreviewDialogProps {
    tasks: NewTask[];
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (selectedTasks: NewTask[]) => void;
}

export function NewTasksPreviewDialog({ tasks, isOpen, onClose, onConfirm }: NewTasksPreviewDialogProps) {
    const [loading, setLoading] = useState(false);
    // 默认选中所有有效的任务
    const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());

    // 当任务列表变化时，默认选中所有有效任务
    useEffect(() => {
        if (isOpen && tasks.length > 0) {
            const validIndices = new Set<number>();
            tasks.forEach((task, index) => {
                if (task.valid !== false) {
                    validIndices.add(index);
                }
            });
            setSelectedIndices(validIndices);
        }
    }, [tasks, isOpen]);

    if (!isOpen) return null;

    const validTasks = tasks.filter(t => t.valid !== false);
    const invalidTasks = tasks.filter(t => t.valid === false);
    const selectedCount = selectedIndices.size;

    const toggleTask = (index: number) => {
        const task = tasks[index];
        if (task.valid === false) return; // 无效任务不能选择

        const newSelected = new Set(selectedIndices);
        if (newSelected.has(index)) {
            newSelected.delete(index);
        } else {
            newSelected.add(index);
        }
        setSelectedIndices(newSelected);
    };

    const toggleAll = () => {
        if (selectedCount === validTasks.length) {
            // 全部取消
            setSelectedIndices(new Set());
        } else {
            // 全选有效任务
            const allValid = new Set<number>();
            tasks.forEach((task, index) => {
                if (task.valid !== false) {
                    allValid.add(index);
                }
            });
            setSelectedIndices(allValid);
        }
    };

    const handleConfirm = async () => {
        const selectedTasks = tasks.filter((_, index) => selectedIndices.has(index));
        if (selectedTasks.length === 0) {
            onClose();
            return;
        }

        setLoading(true);
        await onConfirm(selectedTasks);
        setLoading(false);
        onClose();
    };

    return (
        <div data-mtf-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-3xl mx-4 overflow-hidden border border-slate-700"
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
                    <div className="flex items-center justify-between mb-4">
                        <p className="text-slate-400 text-sm">
                            选择要添加到队列的任务：
                        </p>
                        {validTasks.length > 0 && (
                            <button
                                onClick={toggleAll}
                                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                            >
                                {selectedCount === validTasks.length ? '取消全选' : '全选'}
                            </button>
                        )}
                    </div>

                    <div className="space-y-3">
                        {tasks.map((task, index) => {
                            const isValid = task.valid !== false;
                            const isSelected = selectedIndices.has(index);

                            return (
                                <div
                                    key={index}
                                    onClick={() => toggleTask(index)}
                                    className={`bg-slate-900/50 border rounded-lg p-4 transition-all ${
                                        isValid
                                            ? isSelected
                                                ? 'border-blue-500 cursor-pointer'
                                                : 'border-slate-700 hover:border-slate-600 cursor-pointer'
                                            : 'border-red-500/30 opacity-60 cursor-not-allowed'
                                    }`}
                                >
                                    <div className="flex items-start gap-3">
                                        {/* 复选框 */}
                                        <div className="flex-shrink-0 pt-0.5">
                                            <div
                                                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                                                    isValid
                                                        ? isSelected
                                                            ? 'bg-blue-600 border-blue-600'
                                                            : 'border-slate-500 hover:border-slate-400'
                                                        : 'border-red-500/50 bg-red-500/10'
                                                }`}
                                            >
                                                {isSelected && isValid && (
                                                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                                    </svg>
                                                )}
                                                {!isValid && (
                                                    <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            {/* 序号和名称 */}
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-slate-700 text-slate-300 text-xs rounded-full">
                                                    {index + 1}
                                                </span>
                                                <span className={`font-medium truncate ${isValid ? 'text-slate-100' : 'text-red-400'}`}>
                                                    {task.name || '(未命名)'}
                                                </span>
                                                {!isValid && (
                                                    <span className="text-xs text-red-400 bg-red-500/20 px-2 py-0.5 rounded">
                                                        {task.error || '无效'}
                                                    </span>
                                                )}
                                            </div>

                                            {/* 命令 */}
                                            <div className="pl-8">
                                                <code className={`text-xs font-mono break-all line-clamp-2 ${isValid ? 'text-emerald-400' : 'text-slate-500'}`}>
                                                    {task.command || '(无命令)'}
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
                            );
                        })}
                    </div>

                    {/* 无效任务提示 */}
                    {invalidTasks.length > 0 && (
                        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                            <p className="text-sm text-red-400">
                                ⚠️ {invalidTasks.length} 个任务因格式错误无法添加
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-between items-center px-5 py-4 border-t border-slate-700 bg-slate-800/50">
                    <span className="text-sm text-slate-400">
                        已选择 <span className="text-blue-400 font-medium">{selectedCount}</span> / {validTasks.length} 个任务
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
                            disabled={loading || selectedCount === 0}
                            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
                                    加载 {selectedCount} 个任务
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
