import { useEffect, useRef, useState } from 'react';
import { useTaskStore } from '../stores/taskStore';
import { api, type Task } from '../api';

interface LogPanelProps {
    taskId: string | null; // 'main' for main log, task ID for task log, null to hide
    onClose: () => void;
    onSelectLog?: (id: string) => void;
}

export function LogPanel({ taskId, onClose, onSelectLog }: LogPanelProps) {
    const { runningTasks, pendingTasks, history, logContent, setLogContent, appendLogContent, showToast } = useTaskStore();
    const wsRef = useRef<WebSocket | null>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const pollRef = useRef<number | null>(null);
    const [logPath, setLogPath] = useState<string>('');

    // Check if showing main log
    const isMainLog = taskId === 'main';

    // Find task by ID (if not main log)
    const task: Task | undefined = isMainLog ? undefined : [...runningTasks, ...pendingTasks, ...history].find(t => t.id === taskId);
    const isRunning = task?.status === 'running';

    useEffect(() => {
        if (!taskId) return;

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
                try {
                    const data = await api.getMainLog();
                    if (data.success) {
                        setLogContent(data.content || '日志为空');
                        setLogPath(data.log_file || '');
                    } else {
                        setLogContent(data.detail || '加载失败');
                    }
                } catch (e: any) {
                    setLogContent(`加载失败: ${e.message}`);
                }
            };

            loadMainLog();
            // Poll every 3 seconds
            pollRef.current = window.setInterval(loadMainLog, 3000);

            return () => {
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
                wsConnected = true;
                setLogContent('');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    appendLogContent(data.content);
                } else if (data.type === 'end') {
                    appendLogContent(`\n\n✅ ${data.message}`);
                } else if (data.type === 'info') {
                    setLogContent(data.message);
                } else if (data.type === 'error') {
                    setLogContent(`⚠️ ${data.message}`);
                }
            };

            ws.onerror = () => {
                // Fallback to polling if WebSocket fails
                if (!wsConnected) {
                    setLogContent('正在获取日志...');
                    // Start polling as fallback
                    pollRef.current = setInterval(() => {
                        api.getTaskLog(taskId!).then(data => {
                            if (data.success) {
                                setLogContent(data.content || '日志为空');
                            }
                        }).catch(() => { });
                    }, 2000);
                }
            };

            if (task?.log_file) {
                setLogPath(task.log_file);
            }

            return () => {
                ws.close();
                if (pollRef.current) {
                    clearInterval(pollRef.current);
                    pollRef.current = null;
                }
            };
        } else {
            // Fetch static log
            api.getTaskLog(taskId!).then(data => {
                if (data.success) {
                    setLogContent(data.content || '日志为空');
                } else {
                    setLogContent(data.detail || '加载失败');
                }
            }).catch(e => setLogContent(`加载失败: ${e.message}`));

            if (task?.log_file) {
                setLogPath(task.log_file);
            }
        }
    }, [taskId, isRunning, isMainLog]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (contentRef.current) {
            contentRef.current.scrollTop = contentRef.current.scrollHeight;
        }
    }, [logContent]);

    const copyCommand = (isWindows: boolean) => {
        if (!logPath) return;
        const cmd = isWindows
            ? `Get-Content -Path "${logPath}" -Wait -Tail 50`
            : `tail -f "${logPath}"`;
        navigator.clipboard.writeText(cmd);
        showToast('已复制', 'success');
    };

    // Build task list for selector
    const allTasks = [...runningTasks, ...pendingTasks, ...history.slice(0, 20)];

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
                    {logPath && (
                        <>
                            <button
                                onClick={() => copyCommand(true)}
                                className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
                                title="复制 PowerShell 命令"
                            >🪟</button>
                            <button
                                onClick={() => copyCommand(false)}
                                className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
                                title="复制 Linux 命令"
                            >🐧</button>
                        </>
                    )}
                    <button
                        onClick={onClose}
                        className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
                    >✕</button>
                </div>
            </div>

            {/* Log file path */}
            {logPath && (
                <div className="px-3 py-1.5 bg-slate-900/50 text-xs text-slate-500 truncate border-b border-slate-700/50">
                    <code>{logPath}</code>
                </div>
            )}

            {/* Log content */}
            <div
                ref={contentRef}
                className="flex-1 p-3 overflow-auto font-mono text-xs text-slate-300 whitespace-pre-wrap bg-slate-900/30"
            >
                {logContent}
            </div>
        </div>
    );
}
