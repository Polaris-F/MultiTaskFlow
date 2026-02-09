import { useEffect, useState } from 'react';
import { useQueueStore } from '../stores/queueStore';
import { useTaskStore } from '../stores/taskStore';

interface AddQueueDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export function AddQueueDialog({ isOpen, onClose }: AddQueueDialogProps) {
    const [name, setName] = useState('');
    const [yamlPath, setYamlPath] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { addQueue } = useQueueStore();
    const { showToast } = useTaskStore();

    useEffect(() => {
        if (isOpen) {
            setName('');
            setYamlPath('');
            setError('');
        }
    }, [isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!name.trim() || !yamlPath.trim()) {
            setError('队列名称和 YAML 路径不能为空');
            showToast('队列名称和 YAML 路径不能为空', 'error');
            return;
        }

        setError('');
        setIsSubmitting(true);

        try {
            const success = await addQueue(name.trim(), yamlPath.trim());
            if (success) {
                showToast('队列已添加', 'success');
                setName('');
                setYamlPath('');
                setError('');
                onClose();
            } else {
                setError('添加失败');
                showToast('添加失败', 'error');
            }
        } catch (e: any) {
            setError(`添加失败: ${e.message}`);
            showToast(`添加失败: ${e.message}`, 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div data-mtf-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-slate-700"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-100">
                        📁 添加任务队列
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
                    {/* Queue Name */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-200">队列名称</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="例如: GPU0-1训练队列"
                            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            autoFocus
                        />
                    </div>

                    {/* YAML Path */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-200">YAML 文件路径</label>
                        <input
                            type="text"
                            value={yamlPath}
                            onChange={(e) => setYamlPath(e.target.value)}
                            placeholder="例如: D:/projects/train/tasks.yaml"
                            className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                        />
                        <p className="text-xs text-slate-500">
                            ⓘ 工作目录将自动设为 YAML 所在文件夹
                        </p>
                    </div>

                    {error && (
                        <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
                            {error}
                        </div>
                    )}

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
                            添加队列
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
