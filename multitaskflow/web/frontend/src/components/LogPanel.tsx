import { useEffect, useRef, useState } from 'react';
import { useTaskStore } from '../stores/taskStore';
import { api, type Task } from '../api';
import { XTerminal } from './XTerminal';

interface LogPanelProps {
    taskId: string | null; // 'main' for main log, task ID for task log, null to hide
    onClose: () => void;
    onSelectLog?: (id: string) => void;
}

// 命令对话框组件
function CommandDialog({ command, title, isOpen, onClose }: {
    command: string;
    title: string;
    isOpen: boolean;
    onClose: () => void;
}) {
    const { showToast } = useTaskStore();

    if (!isOpen) return null;

    const copyToClipboard = () => {
        // 优先使用 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(command)
                .then(() => showToast('已复制', 'success'))
                .catch(() => fallbackCopy());
        } else {
            fallbackCopy();
        }
    };

    const fallbackCopy = () => {
        // Fallback: 使用传统的 execCommand 方法
        try {
            const textArea = document.createElement('textarea');
            textArea.value = command;
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

    return (
        <div data-mtf-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-xl mx-4 overflow-hidden border border-slate-700"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
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
                <div className="p-5 space-y-3">
                    <p className="text-sm text-slate-400">复制以下命令在终端中实时查看日志：</p>
                    <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-3 overflow-x-auto">
                        <code className="text-sm text-emerald-400 font-mono whitespace-pre-wrap break-all">
                            {command}
                        </code>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 px-5 py-4 border-t border-slate-700 bg-slate-800/50">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
                    >
                        关闭
                    </button>
                    <button
                        onClick={copyToClipboard}
                        className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors flex items-center gap-2"
                    >
                        📋 复制命令
                    </button>
                </div>
            </div>
        </div>
    );
}

export function LogPanel({ taskId, onClose, onSelectLog }: LogPanelProps) {
    const { runningTasks, pendingTasks, history, logContent, setLogContent, appendLogContent, showToast } = useTaskStore();
    const wsRef = useRef<WebSocket | null>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const pollRef = useRef<number | null>(null);
    const [logPath, setLogPath] = useState<string>('');

    // 命令对话框状态
    const [commandDialog, setCommandDialog] = useState<{ isOpen: boolean; command: string; title: string }>({
        isOpen: false,
        command: '',
        title: '',
    });

    // Check if showing main log
    const isMainLog = taskId === 'main';

    // Find task by ID (if not main log)
    const task: Task | undefined = isMainLog ? undefined : [...runningTasks, ...pendingTasks, ...history].find(t => t.id === taskId);
    const isRunning = task?.status === 'running';

    useEffect(() => {
        if (!taskId) return;

        // 用于取消异步操作的标记
        let cancelled = false;

        // Close existing WebSocket
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        // Clear existing poll
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }

        setLogContent('加载中...');
        setLogPath('');

        if (isMainLog) {
            // Load main log with polling
            const loadMainLog = async () => {
                if (cancelled) return;
                try {
                    const data = await api.getMainLog();
                    if (cancelled) return;  // 检查是否已取消
                    if (data.success) {
                        setLogContent(data.content || '日志为空');
                        setLogPath(data.log_file || '');
                    } else {
                        setLogContent(data.detail || '加载失败');
                    }
                } catch (e: any) {
                    if (cancelled) return;
                    setLogContent(`加载失败: ${e.message}`);
                }
            };

            loadMainLog();
            // Poll every 3 seconds
            pollRef.current = window.setInterval(loadMainLog, 3000);

            return () => {
                cancelled = true;
                if (pollRef.current) {
                    clearInterval(pollRef.current);
                    pollRef.current = null;
                }
            };
        } else if (isRunning) {
            // Real-time log via WebSocket
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/logs/${taskId}`;

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;
            let wsConnected = false;

            ws.onopen = () => {
                if (cancelled) {
                    ws.close();
                    return;
                }
                wsConnected = true;
                setLogContent('');
            };

            ws.onmessage = (event) => {
                if (cancelled) return;
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'init') {
                        // 初始化消息包含日志文件路径
                        if (data.log_file) {
                            setLogPath(data.log_file);
                        }
                    } else if (data.type === 'log') {
                        appendLogContent(data.content);
                    } else if (data.type === 'end') {
                        appendLogContent(`\n\n✅ ${data.message}`);
                    } else if (data.type === 'info') {
                        setLogContent(data.message);
                    } else if (data.type === 'error') {
                        setLogContent(`⚠️ ${data.message}`);
                    }
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            ws.onerror = () => {
                if (cancelled) return;
                if (!wsConnected) {
                    setLogContent('WebSocket 连接失败');
                }
            };

            ws.onclose = () => {
                wsRef.current = null;
            };

            return () => {
                cancelled = true;
                if (wsRef.current) {
                    wsRef.current.close();
                    wsRef.current = null;
                }
            };
        } else {
            // Load historical log for completed tasks
            const loadTaskLog = async () => {
                try {
                    const data = await api.getTaskLog(taskId);
                    if (cancelled) return;  // 关键：检查是否已取消
                    if (data.success) {
                        setLogContent(data.content || '日志为空');
                        setLogPath(data.log_file || '');
                    } else {
                        setLogContent(data.detail || '加载失败');
                    }
                } catch (e: any) {
                    if (cancelled) return;
                    setLogContent(`加载失败: ${e.message}`);
                }
            };
            loadTaskLog();

            return () => {
                cancelled = true;
            };
        }
    }, [taskId, isMainLog, isRunning, setLogContent, appendLogContent]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (contentRef.current) {
            contentRef.current.scrollTop = contentRef.current.scrollHeight;
        }
    }, [logContent]);

    const showCommand = (isWindows: boolean) => {
        if (!logPath) {
            showToast('日志路径未获取', 'error');
            return;
        }
        const cmd = isWindows
            ? `Get-Content -Path "${logPath}" -Wait -Tail 50`
            : `tail -f "${logPath}"`;

        setCommandDialog({
            isOpen: true,
            command: cmd,
            title: isWindows ? '🪟 PowerShell 命令' : '🐧 Linux 命令',
        });
    };

    // Build task list for selector (去重)
    const allTasksMap = new Map();
    [...runningTasks, ...pendingTasks, ...history.slice(0, 20)].forEach(task => {
        if (!allTasksMap.has(task.id)) {
            allTasksMap.set(task.id, task);
        }
    });
    const allTasks = Array.from(allTasksMap.values());

    return (
        <div className="w-full h-full flex flex-col bg-slate-800/50 rounded-lg overflow-hidden border-l border-slate-700">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 bg-slate-800 gap-2">
                {/* Log selector */}
                <select
                    value={taskId || 'main'}
                    onChange={(e) => onSelectLog?.(e.target.value)}
                    className="flex-1 min-w-0 bg-slate-700 text-slate-200 text-sm rounded px-2 py-1 border-none focus:outline-none focus:ring-1 focus:ring-blue-500 truncate"
                >
                    <option value="main">📋 主日志 (TaskFlow)</option>
                    {allTasks.map(t => (
                        <option key={t.id} value={t.id}>
                            {t.status === 'running' ? '⚡' : t.status === 'completed' ? '✅' : t.status === 'failed' ? '❌' : '⏳'} {t.name}
                        </option>
                    ))}
                </select>
                <div className="flex gap-1 flex-shrink-0">
                    <button
                        onClick={() => showCommand(true)}
                        className={`px-2 py-1 text-xs rounded ${logPath ? 'bg-slate-700 hover:bg-slate-600 text-slate-300' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
                        title="PowerShell 命令"
                        disabled={!logPath}
                    >🪟</button>
                    <button
                        onClick={() => showCommand(false)}
                        className={`px-2 py-1 text-xs rounded ${logPath ? 'bg-slate-700 hover:bg-slate-600 text-slate-300' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
                        title="Linux 命令"
                        disabled={!logPath}
                    >🐧</button>
                    <button
                        onClick={onClose}
                        className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
                    >✕</button>
                </div>
            </div>

            {/* Log content - xterm.js terminal */}
            <div className="flex-1 overflow-hidden">
                <XTerminal content={logContent} />
            </div>

            {/* 命令对话框 */}
            <CommandDialog
                command={commandDialog.command}
                title={commandDialog.title}
                isOpen={commandDialog.isOpen}
                onClose={() => setCommandDialog(prev => ({ ...prev, isOpen: false }))}
            />
        </div>
    );
}
