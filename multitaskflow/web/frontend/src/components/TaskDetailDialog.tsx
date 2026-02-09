import { useState, useEffect } from 'react';
import { type Task, api } from '../api';
import { useTaskStore } from '../stores/taskStore';

interface TaskDetailDialogProps {
    task: Task | null;
    isOpen: boolean;
    onClose: () => void;
    onViewLog: (id: string) => void;
}

// 状态配置（与 TaskTable 保持一致）
const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
    'running': { color: 'text-emerald-400', label: '运行中' },
    'pending': { color: 'text-slate-400', label: '等待中' },
    'completed': { color: 'text-blue-400', label: '已完成' },
    'failed': { color: 'text-red-400', label: '失败' },
    'stopped': { color: 'text-amber-400', label: '已停止' },
};

export function TaskDetailDialog({ task, isOpen, onClose, onViewLog }: TaskDetailDialogProps) {
    const { showToast, deleteTask, moveTask, refreshTasks, refreshHistory } = useTaskStore();

    // 编辑模式状态
    const [isEditMode, setIsEditMode] = useState(false);
    const [editName, setEditName] = useState('');
    const [editCommand, setEditCommand] = useState('');
    const [editNote, setEditNote] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // 重置编辑状态
    useEffect(() => {
        if (task && isOpen) {
            setEditName(task.name);
            setEditCommand(task.command);
            setEditNote(task.note || '');
            setIsEditMode(false);  // 打开时默认查看模式
        }
    }, [task, isOpen]);

    if (!isOpen || !task) return null;

    const hasLog = !!task.log_file || task.status === 'running';
    const isPending = task.status === 'pending';
    const isRunning = task.status === 'running';
    const isFinished = task.status === 'failed' || task.status === 'stopped' || task.status === 'completed';
    const statusConfig = STATUS_CONFIG[task.status] || { color: 'text-slate-400', label: task.status };

    const copyToClipboard = (text: string) => {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => showToast('已复制', 'success'))
                .catch(() => fallbackCopy(text));
        } else {
            fallbackCopy(text);
        }
    };

    const fallbackCopy = (text: string) => {
        try {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('已复制', 'success');
        } catch (e) {
            showToast('请手动选中复制', 'info');
        }
    };

    const handleDelete = async () => {
        if (confirm(`确认删除任务 "${task.name}"？`)) {
            await deleteTask(task.id);
            onClose();
        }
    };

    const handleMove = async (direction: number) => {
        await moveTask(task.id, direction);
        showToast(direction < 0 ? '已上移' : '已下移', 'success');
    };

    const handleSave = async () => {
        if (!editName.trim() || !editCommand.trim()) {
            showToast('名称和命令不能为空', 'error');
            return;
        }

        setIsSubmitting(true);
        try {
            const result = await api.updateTask(task.id, {
                name: editName.trim(),
                command: editCommand.trim(),
                note: editNote.trim() || undefined,
            });
            if (result.id) {
                showToast('任务已更新', 'success');
                await refreshTasks();
                setIsEditMode(false);
            } else {
                showToast(result.detail || '更新失败', 'error');
            }
        } catch (e: any) {
            showToast(`更新失败: ${e.message}`, 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleCancelEdit = () => {
        setEditName(task.name);
        setEditCommand(task.command);
        setEditNote(task.note || '');
        setIsEditMode(false);
    };

    const handleRetry = async () => {
        setIsSubmitting(true);
        try {
            const result = await api.retryTask(task.id);
            if (result.success) {
                showToast('任务已加入队列', 'success');
                await refreshTasks();
                await refreshHistory();  // 同时刷新历史记录
                onClose();
            } else {
                showToast(result.detail || '重试失败', 'error');
            }
        } catch (e: any) {
            showToast(`重试失败: ${e.message}`, 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    // 按钮禁用原因
    const getDisabledReason = (action: string): string | null => {
        if (action === 'move' || action === 'edit') {
            if (isRunning) return '运行中';
            if (!isPending) return '已结束';
            return null;
        }
        if (action === 'delete') {
            if (isRunning) return '运行中';
            return null;
        }
        if (action === 'log') {
            return hasLog ? null : '暂无日志';
        }
        if (action === 'retry') {
            if (!isFinished) return '任务未结束';
            return null;
        }
        return null;
    };

    return (
        <div data-mtf-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-4xl mx-4 overflow-hidden border border-slate-700"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header - 在查看模式显示状态标签 */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                    <div className="flex items-center gap-3">
                        <h2 className="text-lg font-semibold text-slate-100">
                            {isEditMode ? '✏️ 编辑任务' : '📋 任务详情'}
                        </h2>
                        {!isEditMode && (
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${task.status === 'running' ? 'bg-emerald-500/20 text-emerald-400' :
                                task.status === 'pending' ? 'bg-slate-600/50 text-slate-400' :
                                    task.status === 'completed' ? 'bg-blue-500/20 text-blue-400' :
                                        task.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                                            'bg-amber-500/20 text-amber-400'
                                }`}>
                                {statusConfig.label}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
                    {isEditMode ? (
                        /* 编辑模式 */
                        <>
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">名称</label>
                                <input
                                    type="text"
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">命令</label>
                                <textarea
                                    value={editCommand}
                                    onChange={(e) => setEditCommand(e.target.value)}
                                    rows={4}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-200 font-mono focus:outline-none focus:border-blue-500 resize-none"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">备注</label>
                                <input
                                    type="text"
                                    value={editNote}
                                    onChange={(e) => setEditNote(e.target.value)}
                                    placeholder="可选"
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                                />
                            </div>
                        </>
                    ) : (
                        /* 查看模式 - 布局与编辑模式保持一致 */
                        <>
                            {/* Task Name */}
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">名称</label>
                                <div className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-100">
                                    {task.name}
                                </div>
                            </div>

                            {/* Command */}
                            <div className="space-y-1">
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">命令</label>
                                    <button
                                        onClick={() => copyToClipboard(task.command)}
                                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                                        title="复制命令"
                                    >
                                        📋 复制
                                    </button>
                                </div>
                                <div className="w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-emerald-400 font-mono whitespace-pre-wrap break-all min-h-[100px]">
                                    {task.command}
                                </div>
                            </div>

                            {/* Note */}
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">备注</label>
                                <div className={`w-full px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-sm ${task.note ? 'text-slate-300' : 'text-slate-500 italic'}`}>
                                    {task.note || '无备注'}
                                </div>
                            </div>

                            {/* Duration */}
                            {task.duration !== undefined && task.duration > 0 && (
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">耗时</label>
                                    <p className="text-slate-300">
                                        {task.duration < 60
                                            ? `${Math.round(task.duration)} 秒`
                                            : task.duration < 3600
                                                ? `${Math.floor(task.duration / 60)} 分 ${Math.round(task.duration % 60)} 秒`
                                                : `${Math.floor(task.duration / 3600)} 小时 ${Math.floor((task.duration % 3600) / 60)} 分`
                                        }
                                    </p>
                                </div>
                            )}

                            {/* Log file path */}
                            {task.log_file && (
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">日志文件</label>
                                    <p className="text-slate-400 font-mono text-xs break-all">{task.log_file}</p>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-slate-700 bg-slate-800/50">
                    {isEditMode ? (
                        /* 编辑模式按钮 */
                        <div className="flex justify-end gap-2">
                            <button
                                onClick={handleCancelEdit}
                                className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={isSubmitting}
                                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white rounded-lg transition-colors"
                            >
                                {isSubmitting ? '保存中...' : '保存'}
                            </button>
                        </div>
                    ) : (
                        /* 查看模式按钮 */
                        <div className="flex flex-wrap justify-between items-center gap-3">
                            {/* Left side - Action buttons */}
                            <div className="flex flex-wrap gap-2">
                                {/* Move Up */}
                                <ActionButton
                                    icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" /></svg>}
                                    label="上移"
                                    onClick={() => handleMove(-1)}
                                    disabled={!isPending}
                                    disabledReason={getDisabledReason('move')}
                                />
                                {/* Move Down */}
                                <ActionButton
                                    icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>}
                                    label="下移"
                                    onClick={() => handleMove(1)}
                                    disabled={!isPending}
                                    disabledReason={getDisabledReason('move')}
                                />
                                {/* Edit - 切换到编辑模式 */}
                                <ActionButton
                                    icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>}
                                    label="编辑"
                                    onClick={() => setIsEditMode(true)}
                                    disabled={!isPending}
                                    disabledReason={getDisabledReason('edit')}
                                />
                                {/* Delete */}
                                <ActionButton
                                    icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>}
                                    label="删除"
                                    onClick={handleDelete}
                                    disabled={isRunning}
                                    disabledReason={getDisabledReason('delete')}
                                    variant="danger"
                                />
                                {/* Retry - 重试已结束的任务 */}
                                <ActionButton
                                    icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
                                    label="重试"
                                    onClick={handleRetry}
                                    disabled={!isFinished || isSubmitting}
                                    disabledReason={getDisabledReason('retry')}
                                    variant="primary"
                                />
                            </div>

                            {/* Right side - View Log and Close */}
                            <div className="flex flex-wrap gap-2">
                                <ActionButton
                                    icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
                                    label="日志"
                                    onClick={() => { onViewLog(task.id); onClose(); }}
                                    disabled={!hasLog}
                                    disabledReason={getDisabledReason('log')}
                                    variant="primary"
                                />
                                <button
                                    onClick={onClose}
                                    className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
                                >
                                    关闭
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// 统一的操作按钮组件
interface ActionButtonProps {
    icon: React.ReactNode;
    label: string;
    onClick: () => void;
    disabled?: boolean;
    disabledReason?: string | null;
    variant?: 'default' | 'primary' | 'danger';
}

function ActionButton({ icon, label, onClick, disabled, disabledReason, variant = 'default' }: ActionButtonProps) {
    const baseClasses = "px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap";

    const variantClasses = {
        default: disabled
            ? 'bg-slate-700/30 text-slate-500 cursor-not-allowed'
            : 'bg-slate-700 hover:bg-slate-600 text-slate-200',
        primary: disabled
            ? 'bg-blue-600/20 text-blue-400/50 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-500 text-white',
        danger: disabled
            ? 'bg-red-600/10 text-red-400/50 cursor-not-allowed'
            : 'bg-red-600/20 hover:bg-red-500 text-red-400 hover:text-white',
    };

    const title = disabled && disabledReason ? `${label} (${disabledReason})` : label;

    return (
        <button
            onClick={disabled ? undefined : onClick}
            className={`${baseClasses} ${variantClasses[variant]}`}
            title={title}
            disabled={disabled}
        >
            {icon}
            <span>{label}</span>
        </button>
    );
}
