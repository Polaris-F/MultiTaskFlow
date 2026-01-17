import { useEffect, useState } from 'react';
import { useTaskStore } from './stores/taskStore';
import { useQueueStore } from './stores/queueStore';
import { Header } from './components/Header';
import { Toolbar } from './components/Toolbar';
import { TaskTable, StatusLegend } from './components/TaskTable';
import { LogPanel } from './components/LogPanel';
import { ToastContainer } from './components/Toast';
import { FilterTabs, type FilterType } from './components/FilterTabs';
import { ResizablePanels } from './components/ResizablePanels';
import { SettingsPanel } from './components/SettingsPanel';
import { TaskDialog } from './components/TaskDialog';
import { QueueTabs } from './components/QueueTabs';
import { AddQueueDialog } from './components/AddQueueDialog';
import { LoginPage } from './components/LoginPage';
import { type Task } from './api';

// 认证状态类型
interface AuthStatus {
  authenticated: boolean;
  auth_enabled: boolean;
}

function App() {
  const { refreshTasks, refreshHistory, refreshQueueStatus, setLogPanelOpen, setCurrentLogTask, runningTasks, pendingTasks, history } = useTaskStore();
  const { fetchQueues, queues, currentQueueId, fetchGlobalGpuUsage } = useQueueStore();

  // 认证状态
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Default to 'main' to show main log on startup
  const [currentLogId, setCurrentLogId] = useState<string>('main');
  const [filter, setFilter] = useState<FilterType>('all');

  // Dialog states
  const [isTaskDialogOpen, setTaskDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isAddQueueDialogOpen, setAddQueueDialogOpen] = useState(false);

  // 检查认证状态
  const checkAuth = async () => {
    try {
      const res = await fetch('/api/auth/status');
      if (res.ok) {
        const data = await res.json();
        setAuthStatus(data);
      }
    } catch (e) {
      // 网络错误，忽略
    } finally {
      setAuthLoading(false);
    }
  };

  // 首次加载时检查认证状态
  useEffect(() => {
    checkAuth();
  }, []);

  // Initial fetch and polling (only when authenticated or auth not enabled)
  useEffect(() => {
    if (authLoading) return;
    if (authStatus?.auth_enabled && !authStatus?.authenticated) return;

    // Fetch queues first
    fetchQueues();
    fetchGlobalGpuUsage();

    // Then fetch tasks for current queue
    refreshTasks();
    refreshHistory();
    refreshQueueStatus();

    const interval = setInterval(() => {
      fetchQueues();
      fetchGlobalGpuUsage();
      refreshTasks();
      refreshHistory();
      refreshQueueStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, [authLoading, authStatus]);

  // Refresh tasks when queue changes
  useEffect(() => {
    if (currentQueueId) {
      refreshTasks();
      refreshHistory();
      refreshQueueStatus();
    }
  }, [currentQueueId]);

  // 当有任务运行时，自动显示运行中任务的日志
  useEffect(() => {
    if (runningTasks.length > 0) {
      // 有运行中的任务，显示第一个运行中任务的日志
      const runningTaskId = runningTasks[0].id;
      setCurrentLogId(runningTaskId);
      setCurrentLogTask(runningTaskId);
    } else if (currentLogId && currentLogId !== 'main') {
      // 没有运行中的任务，但当前显示的是某个任务日志
      // 检查该任务是否还存在
      const taskExists = [...pendingTasks, ...history].some(t => t.id === currentLogId);
      if (!taskExists) {
        // 任务不存在了，回退到主日志
        setCurrentLogId('main');
        setCurrentLogTask(null);
      }
      // 如果任务存在（已完成/失败），保持显示该任务日志
    }
  }, [runningTasks, pendingTasks, history]);

  // Check if current queue has YAML loaded
  const hasQueue = queues.length > 0 && currentQueueId;

  // Calculate filter counts
  const filterCounts: Record<FilterType, number> = {
    all: runningTasks.length + pendingTasks.length + history.length,
    running: runningTasks.length,
    pending: pendingTasks.length,
    completed: history.filter(t => t.status === 'completed').length,
    failed: history.filter(t => t.status === 'failed').length,
    stopped: history.filter(t => t.status === 'stopped').length,
  };

  // Handle log view from task table
  const handleViewLog = (taskId: string) => {
    setCurrentLogId(taskId);
    setCurrentLogTask(taskId);
    setLogPanelOpen(true);
  };

  // Handle log selection from dropdown
  const handleSelectLog = (logId: string) => {
    setCurrentLogId(logId);
    if (logId !== 'main') {
      setCurrentLogTask(logId);
    } else {
      setCurrentLogTask(null);
    }
  };

  const handleCloseLog = () => {
    setCurrentLogId('');
    setCurrentLogTask(null);
    setLogPanelOpen(false);
  };

  // Task dialog handlers
  const handleAddTask = () => {
    setEditingTask(null);
    setTaskDialogOpen(true);
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setTaskDialogOpen(true);
  };

  const handleCloseTaskDialog = () => {
    setTaskDialogOpen(false);
    setEditingTask(null);
  };

  // Queue dialog handlers
  const handleAddQueue = () => {
    setAddQueueDialogOpen(true);
  };

  const handleCloseAddQueueDialog = () => {
    setAddQueueDialogOpen(false);
  };

  // ESC to close log panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && currentLogId) {
        handleCloseLog();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentLogId]);

  // 加载中
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0f1a]">
        <div className="text-slate-400">
          <svg className="w-8 h-8 animate-spin mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          加载中...
        </div>
      </div>
    );
  }

  // 需要登录或设置密码
  if (authStatus && (!authStatus.auth_enabled || !authStatus.authenticated)) {
    return (
      <LoginPage
        onLogin={checkAuth}
        authEnabled={authStatus.auth_enabled}
      />
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0f1a] text-slate-100">
      <Header />

      <div className="flex-1 flex flex-col p-4 gap-4 min-h-0">
        {/* Queue tabs */}
        <div className="flex items-center justify-between gap-4">
          <QueueTabs onAddQueue={handleAddQueue} />
        </div>

        {/* Content area - only show if queue is loaded */}
        {hasQueue ? (
          <>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <FilterTabs current={filter} onChange={setFilter} counts={filterCounts} />
              <StatusLegend />
              <Toolbar onAddTask={handleAddTask} />
            </div>

            <ResizablePanels
              leftPanel={<TaskTable onViewLog={handleViewLog} onEditTask={handleEditTask} filter={filter} />}
              rightPanel={currentLogId ? <LogPanel taskId={currentLogId} onClose={handleCloseLog} onSelectLog={handleSelectLog} /> : null}
              defaultLeftWidth={50}
              minLeftWidth={25}
              maxLeftWidth={85}
            />
          </>
        ) : (
          /* Empty state - no queue loaded */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="text-6xl">📁</div>
              <h2 className="text-xl font-medium text-slate-300">没有加载任务队列</h2>
              <p className="text-slate-500">点击上方"添加队列"按钮添加 YAML 配置文件</p>
              <button
                onClick={handleAddQueue}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
              >
                + 添加任务队列
              </button>
            </div>
          </div>
        )}
      </div>

      <ToastContainer />
      <SettingsPanel />
      <TaskDialog
        isOpen={isTaskDialogOpen}
        onClose={handleCloseTaskDialog}
        editTask={editingTask}
      />
      <AddQueueDialog
        isOpen={isAddQueueDialogOpen}
        onClose={handleCloseAddQueueDialog}
      />
    </div>
  );
}

export default App;
