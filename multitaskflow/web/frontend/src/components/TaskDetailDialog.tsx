import { type Task } from '../api';
import { useTaskStore } from '../stores/taskStore';

interface TaskDetailDialogProps {
    task: Task | null;
    isOpen: boolean;
    onClose: () => void;
    onViewLog: (id: string) => void;
    onEdit?: (task: Task) => void;
}

// 状态配置（与 TaskTable 保持一致）
const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
    'running': { color: 'text-emerald-400', label: '运行中' },
    'pending': { color: 'text-slate-400', label: '等待中' },
    'completed': { color: 'text-blue-400', label: '已完成' },
    'failed': { color: 'text-red-400', label: '失败' },
    'stopped': { color: 'text-amber-400', label: '已停止' },
};

export function TaskDetailDialog({ task, isOpen, onClose, onViewLog, onEdit }: TaskDetailDialogProps) {
    const { showToast, deleteTask, moveTask } = useTaskStore();

    if (!isOpen || !task) return null;

    const hasLog = !!task.log_file || task.status === 'running';
    const isPending = task.status === 'pending';
    const isRunning = task.status === 'running';
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

    const handleDelete = () => {
        if (confirm(`确认删除任务 "${task.name}"？`)) {
            deleteTask(task.id);
            onClose();
            showToast('任务已删除', 'success');
        }
    };

    const handleMove = (direction: number) => {
        moveTask(task.id, direction);
        showToast(direction < 0 ? '已上移' : '已下移', 'success');
    };

    // 按钮禁用原因
    const getDisabledReason = (action: string): string | null => {
        if (action === 'move' || action === 'edit' || action === 'delete') {
            if (isRunning) return '运行中';
            if (!isPending) return '已结束';
            return null;
        }
        if (action === 'log') {
            return hasLog ? null : '暂无日志';
        }
        return null;
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
                        📋 任务详情
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

                {/* Content */}
                <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
                    {/* Task Name */}
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">名称</label>
                        <p className="text-slate-100 font-medium">{task.name}</p>
                    </div>

                    {/* Status */}
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">状态</label>
                        <p className={`font-medium ${statusConfig.color}`}>
                            {statusConfig.label}
                        </p>
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
                        <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-3 overflow-x-auto">
                            <code className="text-sm text-emerald-400 font-mono whitespace-pre-wrap break-all">
                                {task.command}
                            </code>
                        </div>
                    </div>

                    {/* Note */}
                    {task.note && (
                        <div className="space-y-1">
                            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">备注</label>
                            <p className="text-slate-300">{task.note}</p>
                        </div>
                    )}

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
                </div>

                {/* Footer - 固定布局按钮 */}
                <div className="px-5 py-4 border-t border-slate-700 bg-slate-800/50">
                    <div className="flex justify-between items-center">
                        {/* Left side - Action buttons (fixed layout) */}
                        <div className="flex gap-2">
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
                            {/* Edit */}
                            <ActionButton
                                icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>}
                                label="编辑"
                                onClick={() => { onEdit?.(task); onClose(); }}
                                disabled={!isPending || !onEdit}
                                disabledReason={getDisabledReason('edit')}
                            />
                            {/* Delete */}
                            <ActionButton
                                icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>}
                                label="删除"
                                onClick={handleDelete}
                                disabled={!isPending}
                                disabledReason={getDisabledReason('delete')}
                                variant="danger"
                            />
                        </div>

                        {/* Right side - Close and View Log buttons */}
                        <div className="flex gap-2">
                            {/* Log */}
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
    const baseClasses = "px-3 py-2 text-sm rounded-lg transition-colors flex items-center gap-1";

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
            <span className="hidden sm:inline">{label}</span>
            {disabled && disabledReason && (
                <span className="text-[10px] opacity-60 hidden md:inline">({disabledReason})</span>
            )}
        </button>
    );
}
