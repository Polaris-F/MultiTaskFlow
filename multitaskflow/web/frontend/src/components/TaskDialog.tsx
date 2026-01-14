import { useState, useEffect } from 'react';
import { useTaskStore } from '../stores/taskStore';
import { api, type Task } from '../api';

interface TaskDialogProps {
    isOpen: boolean;
    onClose: () => void;
    editTask?: Task | null; // If provided, dialog is in edit mode
}

export function TaskDialog({ isOpen, onClose, editTask }: TaskDialogProps) {
    const [name, setName] = useState('');
    const [command, setCommand] = useState('');
    const [note, setNote] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { showToast, refreshTasks } = useTaskStore();

    const isEditMode = !!editTask;

    // Populate fields when editing
    useEffect(() => {
        if (editTask) {
            setName(editTask.name);
            setCommand(editTask.command);
            setNote(editTask.note || '');
        } else {
            setName('');
            setCommand('');
            setNote('');
        }
    }, [editTask, isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!name.trim() || !command.trim()) {
            showToast('任务名称和命令不能为空', 'error');
            return;
        }

        setIsSubmitting(true);

        try {
            if (isEditMode && editTask) {
                // Update existing task - API returns updated task object
                const result = await api.updateTask(editTask.id, {
                    name: name.trim(),
                    command: command.trim(),
                    note: note.trim() || undefined,
                });
                // Check if result has id (successful update returns task object)
                if (result.id) {
                    showToast('任务已更新', 'success');
                    await refreshTasks();
                    onClose();
                } else {
                    showToast(result.detail || '更新失败', 'error');
                }
            } else {
                // Add new task - API returns new task object
                const result = await api.addTask({
                    name: name.trim(),
                    command: command.trim(),
                    note: note.trim() || undefined,
                });
                // Check if result has id (successful add returns task object)
                if (result.id) {
                    showToast('任务已添加', 'success');
                    await refreshTasks();
                    onClose();
                } else {
                    showToast(result.detail || '添加失败', 'error');
                }
            }
        } catch (e: any) {
            showToast(`操作失败: ${e.message}`, 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-slate-700"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-100">
                        {isEditMode ? '✏️ 编辑任务' : '➕ 添加新任务'}
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

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-5 space-y-4">
                    {/* Task Name */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-200">任务名称</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="例如: 模型训练 ResNet50"
                            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            autoFocus
                        />
                    </div>

                    {/* Command */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-200">执行命令</label>
                        <textarea
                            value={command}
                            onChange={(e) => setCommand(e.target.value)}
                            placeholder="例如: python train.py --model=resnet50 --epochs=100"
                            rows={3}
                            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm resize-none"
                        />
                    </div>

                    {/* Note */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-200">备注 <span className="text-slate-500">(可选)</span></label>
                        <input
                            type="text"
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            placeholder="添加备注信息..."
                            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>

                    {/* Buttons */}
                    <div className="flex justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
                        >
                            取消
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {isSubmitting && (
                                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                            )}
                            {isEditMode ? '保存修改' : '添加任务'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
