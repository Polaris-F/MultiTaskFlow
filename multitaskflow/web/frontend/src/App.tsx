import { useEffect, useState } from 'react';
import { useTaskStore } from './stores/taskStore';
import { useQueueStore } from './stores/queueStore';
import { Header } from './components/Header';
import { Toolbar } from './components/Toolbar';
import { TaskTable } from './components/TaskTable';
import { LogPanel } from './components/LogPanel';
import { ToastContainer } from './components/Toast';
import { FilterTabs, type FilterType } from './components/FilterTabs';
import { ResizablePanels } from './components/ResizablePanels';
import { SettingsPanel } from './components/SettingsPanel';
import { TaskDialog } from './components/TaskDialog';
import { QueueTabs } from './components/QueueTabs';
import { AddQueueDialog } from './components/AddQueueDialog';
import { type Task } from './api';

function App() {
  const { refreshTasks, refreshHistory, refreshQueueStatus, setLogPanelOpen, setCurrentLogTask, runningTasks, pendingTasks, history } = useTaskStore();
  const { fetchQueues, queues, currentQueueId, fetchGlobalGpuUsage } = useQueueStore();

  // Default to 'main' to show main log on startup
  const [currentLogId, setCurrentLogId] = useState<string>('main');
  const [filter, setFilter] = useState<FilterType>('all');

  // Dialog states
  const [isTaskDialogOpen, setTaskDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isAddQueueDialogOpen, setAddQueueDialogOpen] = useState(false);

  // Initial fetch and polling
  useEffect(() => {
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
  }, []);

  // Refresh tasks when queue changes
  useEffect(() => {
    if (currentQueueId) {
      // Reset log to main log when switching queues
      setCurrentLogId('main');
      setCurrentLogTask(null);

      refreshTasks();
      refreshHistory();
      refreshQueueStatus();
    }
  }, [currentQueueId]);

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
