import { useState, useRef } from 'react';
import { useTaskStore } from '../stores/taskStore';
import { type Task } from '../api';
import { type FilterType } from './FilterTabs';

function StatusIcon({ status }: { status: string }) {
    switch (status) {
        case 'running':
            return <span className="text-blue-400 font-bold" title="运行中">⚡</span>;
        case 'pending':
            return <span className="text-slate-500" title="等待中">⏳</span>;
        case 'completed':
            return <span className="text-emerald-400" title="完成">✅</span>;
        case 'failed':
            return <span className="text-red-400" title="失败">❌</span>;
        default:
            return <span className="text-slate-500" title="未知">◯</span>;
    }
}

function formatDuration(seconds?: number): string {
    if (!seconds || seconds < 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
}

// Column keys in order: note is last (before actions which is fixed)
const COLUMNS = [
    { key: 'order', label: '#', minWidth: 3, defaultWidth: 5 },
    { key: 'status', label: '状态', minWidth: 4, defaultWidth: 6 },
    { key: 'name', label: '名称', minWidth: 10, defaultWidth: 18 },
    { key: 'command', label: '命令', minWidth: 15, defaultWidth: 30 },
    { key: 'duration', label: '耗时', minWidth: 5, defaultWidth: 8 },
    { key: 'actions', label: '操作', minWidth: 8, defaultWidth: 13 },
    { key: 'note', label: '备注', minWidth: 10, defaultWidth: 20 },
] as const;

type ColumnKey = typeof COLUMNS[number]['key'];

interface TaskRowProps {
    task: Task;
    index: number;
    onViewLog: (id: string) => void;
    onEdit: (task: Task) => void;
    columnWidths: Record<ColumnKey, number>;
}

function TaskRow({ task, index, onViewLog, onEdit, columnWidths }: TaskRowProps) {
    const { runTask, stopTask, deleteTask, moveTask } = useTaskStore();
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

    const handleDelete = () => {
        if (confirm(`删除任务 "${task.name}"？`)) {
            deleteTask(task.id);
        }
    };

    return (
        <tr className={`border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors ${rowBg}`}>
            <td className="px-2 py-2.5 text-center text-slate-500 text-sm" style={{ width: `${columnWidths.order}%` }}>
                {index + 1}
            </td>
            <td className="px-2 py-2.5 text-center" style={{ width: `${columnWidths.status}%` }}>
                <StatusIcon status={task.status} />
            </td>
            <td className="px-2 py-2.5 text-slate-200 font-medium text-sm truncate" style={{ width: `${columnWidths.name}%` }} title={task.name}>
                {task.name}
            </td>
            <td className="px-2 py-2.5" style={{ width: `${columnWidths.command}%` }}>
                <span className="font-mono text-xs text-slate-400 truncate block" title={task.command}>
                    {task.command}
                </span>
            </td>
            <td className="px-2 py-2.5 text-center text-sm text-slate-400" style={{ width: `${columnWidths.duration}%` }}>
                {duration}
            </td>
            <td className="px-2 py-2.5" style={{ width: `${columnWidths.actions}%` }}>
                <div className="flex gap-1 justify-center flex-wrap items-center">
                    {isPending && (
                        <>
                            <button onClick={() => moveTask(task.id, -1)} className="p-1.5 hover:bg-slate-600 rounded text-slate-400 hover:text-white transition-colors" title="上移">
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                                </svg>
                            </button>
                            <button onClick={() => moveTask(task.id, 1)} className="p-1.5 hover:bg-slate-600 rounded text-slate-400 hover:text-white transition-colors" title="下移">
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            <button onClick={() => runTask(task.id)} className="p-1.5 hover:bg-emerald-500 bg-emerald-600/60 rounded text-white transition-colors" title="开始">
                                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M8 5v14l11-7z" />
                                </svg>
                            </button>
                            <button onClick={handleDelete} className="p-1.5 hover:bg-red-500 rounded text-red-400 hover:text-white transition-colors" title="删除">
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </>
                    )}
                    {isRunning && (
                        <button onClick={() => stopTask(task.id)} className="p-1.5 hover:bg-amber-500 bg-amber-600/60 rounded text-white transition-colors" title="停止">
                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                                <rect x="6" y="6" width="12" height="12" rx="1" />
                            </svg>
                        </button>
                    )}
                    {hasLog && (
                        <button onClick={() => onViewLog(task.id)} className="flex items-center gap-1 px-2 py-1 hover:bg-blue-500 bg-blue-600/60 rounded text-white text-xs transition-colors" title="查看日志">
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            查看
                        </button>
                    )}
                    {/* Edit button - available for pending tasks */}
                    {isPending && (
                        <button onClick={() => onEdit(task)} className="p-1.5 hover:bg-slate-500 rounded text-slate-400 hover:text-white transition-colors" title="编辑">
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </button>
                    )}
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

export function TaskTable({ onViewLog, onEditTask, filter }: { onViewLog: (id: string) => void; onEditTask: (task: Task) => void; filter: FilterType }) {
    const tableRef = useRef<HTMLTableElement>(null);

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
                                className={col.key === 'order' || col.key === 'status' || col.key === 'duration' ? 'text-center' : ''}
                                isLast={i === COLUMNS.length - 1}
                            />
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {allTasks.length === 0 ? (
                        <tr>
                            <td colSpan={7} className="text-center py-20 text-slate-500">
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
                                onEdit={onEditTask}
                                columnWidths={columnWidths}
                            />
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
}
