import { useTaskStore } from '../stores/taskStore';
import { useSettingsStore } from '../stores/settingsStore';

export function Header() {
    const { queueStatus, runningTasks } = useTaskStore();
    const { setSettingsOpen } = useSettingsStore();

    const statusText = queueStatus.running
        ? '队列运行中'
        : runningTasks.length > 0
            ? `运行 ${runningTasks.length}`
            : '空闲';

    const isActive = queueStatus.running || runningTasks.length > 0;

    return (
        <header className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                    🚀 MultiTaskFlow
                </h1>
                <span className="text-xs text-slate-500">v1.2.0</span>
            </div>
            <div className="flex items-center gap-3">
                <span
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${isActive
                        ? 'bg-emerald-500/20 text-emerald-400 animate-pulse-glow'
                        : 'bg-slate-700 text-slate-400'
                        }`}
                >
                    {statusText}
                </span>

                {/* Settings button */}
                <button
                    onClick={() => setSettingsOpen(true)}
                    className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
                    title="设置"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </button>
            </div>
        </header>
    );
}
