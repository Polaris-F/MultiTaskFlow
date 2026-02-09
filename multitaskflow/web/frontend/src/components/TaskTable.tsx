import { useState, useRef } from 'react';
import { useTaskStore } from '../stores/taskStore';
import { type Task } from '../api';
import { type FilterType } from './FilterTabs';
import { TaskDetailDialog } from './TaskDetailDialog';

// 状态配置
const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
    'running': { color: 'bg-emerald-400 animate-pulse', label: '运行中' },
    'pending': { color: 'bg-slate-400', label: '等待中' },
    'completed': { color: 'bg-blue-400', label: '已完成' },
    'failed': { color: 'bg-red-400', label: '失败' },
    'stopped': { color: 'bg-amber-400', label: '已停止' },
};

// 状态圆点组件
function StatusDot({ status }: { status: string }) {
    const config = STATUS_CONFIG[status] || { color: 'bg-slate-500', label: status };
    return (
        <span
            className={`inline-block w-2 h-2 rounded-full ${config.color}`}
            title={config.label}
        />
    );
}

// 状态图例组件 - 导出供其他组件使用
export function StatusLegend() {
    return (
        <div className="flex items-center gap-4 text-xs text-slate-400">
            {Object.entries(STATUS_CONFIG).map(([status, config]) => (
                <div key={status} className="flex items-center gap-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${config.color.replace(' animate-pulse', '')}`} />
                    <span>{config.label}</span>
                </div>
            ))}
        </div>
    );
}

function formatDuration(seconds?: number): string {
    if (seconds == null || seconds < 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
}

// 简化列：移除状态列
const COLUMNS = [
    { key: 'order', label: '#', minWidth: 3, defaultWidth: 4 },
    { key: 'name', label: '名称', minWidth: 12, defaultWidth: 22 },
    { key: 'command', label: '命令', minWidth: 15, defaultWidth: 32 },
    { key: 'duration', label: '耗时', minWidth: 5, defaultWidth: 7 },
    { key: 'actions', label: '操作', minWidth: 10, defaultWidth: 12 },
    { key: 'note', label: '备注', minWidth: 10, defaultWidth: 23 },
] as const;

type ColumnKey = typeof COLUMNS[number]['key'];

interface TaskRowProps {
    task: Task;
    index: number;
    onViewLog: (id: string) => void;
    onViewDetail: (task: Task) => void;
    columnWidths: Record<ColumnKey, number>;
}

function TaskRow({ task, index, onViewLog, onViewDetail, columnWidths }: TaskRowProps) {
    const { runTask, stopTask } = useTaskStore();
    const isRunning = task.status === 'running';
    const isPending = task.status === 'pending';
    const hasLog = !!task.log_file || isRunning;
    const duration = formatDuration(task.duration);

    const rowBg = isRunning
        ? 'bg-blue-500/10'
        : task.status === 'failed'
            ? 'bg-red-500/10'
            : task.status === 'completed'
                ? 'opacity-60'
                : '';

    return (
        <tr
            className={`border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors cursor-pointer ${rowBg}`}
            onClick={() => onViewDetail(task)}
        >
            <td className="px-2 py-2.5 text-center text-slate-500 text-sm" style={{ width: `${columnWidths.order}%` }}>
                {index + 1}
            </td>
            <td className="px-2 py-2.5" style={{ width: `${columnWidths.name}%` }}>
                <div className="flex items-center gap-2">
                    <StatusDot status={task.status} />
                    <span className="text-slate-200 font-medium text-sm truncate" title={task.name}>
                        {task.name}
                    </span>
                </div>
            </td>
            <td className="px-2 py-2.5" style={{ width: `${columnWidths.command}%` }}>
                <span className="font-mono text-xs text-slate-400 truncate block" title={task.command}>
                    {task.command}
                </span>
            </td>
            <td className="px-2 py-2.5 text-center text-sm text-slate-400" style={{ width: `${columnWidths.duration}%` }}>
                {duration}
            </td>
            <td className="px-2 py-2.5" style={{ width: `${columnWidths.actions}%` }} onClick={(e) => e.stopPropagation()}>
                <div className="flex gap-1 justify-center items-center">
                    {/* 开始/停止按钮 - 复用同一个位置 */}
                    {isPending ? (
                        <button
                            onClick={() => runTask(task.id)}
                            className="p-1.5 hover:bg-emerald-500 bg-emerald-600/60 rounded text-white transition-colors"
                            title="开始"
                        >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M8 5v14l11-7z" />
                            </svg>
                        </button>
                    ) : isRunning ? (
                        <button
                            onClick={() => stopTask(task.id)}
                            className="p-1.5 hover:bg-amber-500 bg-amber-600/60 rounded text-white transition-colors"
                            title="停止"
                        >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <rect x="6" y="6" width="12" height="12" rx="1" />
                            </svg>
                        </button>
                    ) : (
                        <button
                            disabled
                            className="p-1.5 rounded text-slate-600 cursor-not-allowed"
                            title="无操作"
                        >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M8 5v14l11-7z" />
                            </svg>
                        </button>
                    )}

                    {/* 日志按钮 - 始终显示，无日志时变灰 */}
                    <button
                        onClick={() => hasLog && onViewLog(task.id)}
                        className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${hasLog
                            ? 'hover:bg-blue-500 bg-blue-600/60 text-white'
                            : 'bg-slate-700/30 text-slate-500 cursor-not-allowed'
                            }`}
                        title={hasLog ? "查看日志" : "暂无日志"}
                        disabled={!hasLog}
                    >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        日志
                    </button>
                </div>
            </td>
            <td className="px-2 py-2.5 text-xs text-slate-400 truncate" style={{ width: `${columnWidths.note}%` }} title={task.note || ''}>
                {task.note || '-'}
            </td>
        </tr>
    );
}

interface ResizableHeaderProps {
    label: string;
    width: number;
    onResizeStart: (e: React.MouseEvent) => void;
    className?: string;
    isLast?: boolean;
}

function ResizableHeader({ label, width, onResizeStart, className = '', isLast = false }: ResizableHeaderProps) {
    return (
        <th
            className={`relative px-2 py-3 select-none ${className}`}
            style={{ width: `${width}%` }}
        >
            {label}
            {!isLast && (
                <div
                    className="absolute right-0 top-2 bottom-2 w-1 cursor-col-resize bg-slate-600 hover:bg-blue-500 active:bg-blue-400 transition-colors rounded"
                    onMouseDown={onResizeStart}
                />
            )}
        </th>
    );
}

export function TaskTable({ onViewLog, filter }: { onViewLog: (id: string) => void; filter: FilterType }) {
    const tableRef = useRef<HTMLTableElement>(null);

    // 详情对话框状态
    const [detailTask, setDetailTask] = useState<Task | null>(null);
    const [showDetail, setShowDetail] = useState(false);

    const handleViewDetail = (task: Task) => {
        setDetailTask(task);
        setShowDetail(true);
    };

    // Column widths as percentages
    const [columnWidths, setColumnWidths] = useState<Record<ColumnKey, number>>(() => {
        const widths: Record<string, number> = {};
        COLUMNS.forEach(col => { widths[col.key] = col.defaultWidth; });
        return widths as Record<ColumnKey, number>;
    });

    // Handle column resize with smooth percentage adjustment
    const handleResizeStart = (colIndex: number) => (e: React.MouseEvent) => {
        e.preventDefault();
        if (!tableRef.current) return;

        const startX = e.clientX;
        const tableWidth = tableRef.current.offsetWidth;
        const col = COLUMNS[colIndex];
        const nextCol = COLUMNS[colIndex + 1];
        if (!nextCol) return;

        const startWidth = columnWidths[col.key];
        const nextStartWidth = columnWidths[nextCol.key];

        const handleMouseMove = (moveEvent: MouseEvent) => {
            const deltaX = moveEvent.clientX - startX;
            const deltaPercent = (deltaX / tableWidth) * 100;

            let newWidth = startWidth + deltaPercent;
            let newNextWidth = nextStartWidth - deltaPercent;

            // Enforce minimums
            if (newWidth < col.minWidth) {
                newNextWidth += (newWidth - col.minWidth);
                newWidth = col.minWidth;
            }
            if (newNextWidth < nextCol.minWidth) {
                newWidth -= (nextCol.minWidth - newNextWidth);
                newNextWidth = nextCol.minWidth;
            }

            setColumnWidths(prev => ({
                ...prev,
                [col.key]: newWidth,
                [nextCol.key]: newNextWidth
            }));
        };

        const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    };

    // Get all tasks and their stable order from store
    const { runningTasks, pendingTasks, history, taskOrder } = useTaskStore();

    // Build task map for quick lookup
    const taskMap = new Map<string, Task>();
    [...runningTasks, ...pendingTasks, ...history].forEach(t => {
        taskMap.set(t.id, t);
    });

    // Get tasks in stable order
    const allTasksRaw = taskOrder
        .filter(id => taskMap.has(id))
        .map(id => taskMap.get(id)!);

    // Apply filter
    const allTasks = allTasksRaw.filter(task => {
        if (filter === 'all') return true;
        if (filter === 'running') return task.status === 'running';
        if (filter === 'pending') return task.status === 'pending';
        if (filter === 'completed') return task.status === 'completed';
        if (filter === 'failed') return task.status === 'failed';
        if (filter === 'stopped') return task.status === 'stopped';
        return true;
    });

    return (
        <div className="w-full h-full overflow-auto bg-slate-800/30 rounded-lg">
            <table ref={tableRef} className="w-full table-fixed">
                <thead className="sticky top-0 bg-slate-800 z-10 shadow-lg">
                    <tr className="text-left text-xs text-slate-400 uppercase tracking-wider">
                        {COLUMNS.map((col, i) => (
                            <ResizableHeader
                                key={col.key}
                                label={col.label}
                                width={columnWidths[col.key]}
                                onResizeStart={handleResizeStart(i)}
                                className={col.key === 'order' || col.key === 'duration' || col.key === 'actions' ? 'text-center' : ''}
                                isLast={i === COLUMNS.length - 1}
                            />
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {allTasks.length === 0 ? (
                        <tr>
                            <td colSpan={6} className="text-center py-20 text-slate-500">
                                暂无任务
                            </td>
                        </tr>
                    ) : (
                        allTasks.map((task, index) => (
                            <TaskRow
                                key={task.id}
                                task={task}
                                index={index}
                                onViewLog={onViewLog}
                                onViewDetail={handleViewDetail}
                                columnWidths={columnWidths}
                            />
                        ))
                    )}
                </tbody>
            </table>

            {/* 任务详情对话框 */}
            <TaskDetailDialog
                task={detailTask}
                isOpen={showDetail}
                onClose={() => setShowDetail(false)}
                onViewLog={onViewLog}
            />
        </div>
    );
}
