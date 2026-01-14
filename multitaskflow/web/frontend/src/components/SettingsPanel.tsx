import { useSettingsStore } from '../stores/settingsStore';

export function SettingsPanel() {
    const {
        isSettingsOpen,
        setSettingsOpen,
        taskNameMinWidth,
        setTaskNameMinWidth,
        tableWrapContent,
        setTableWrapContent,
        canHideCommand,
        setCanHideCommand,
        canHideDuration,
        setCanHideDuration,
        canHideActions,
        setCanHideActions,
        canHideNote,
        setCanHideNote,
    } = useSettingsStore();

    if (!isSettingsOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSettingsOpen(false)}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-slate-700"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-100">⚙️ 页面设置</h2>
                    <button
                        onClick={() => setSettingsOpen(false)}
                        className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 space-y-6">
                    {/* Task Name Min Width */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <label className="text-sm font-medium text-slate-200">任务名称最小宽度</label>
                            <span className="text-sm text-blue-400 font-mono">{taskNameMinWidth}%</span>
                        </div>
                        <input
                            type="range"
                            min="10"
                            max="40"
                            value={taskNameMinWidth}
                            onChange={(e) => setTaskNameMinWidth(Number(e.target.value))}
                            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                        <p className="text-xs text-slate-500">任务名称列的最小宽度百分比，此列永不隐藏</p>
                    </div>

                    <hr className="border-slate-700" />

                    {/* Table Content Wrapping */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <label className="text-sm font-medium text-slate-200">表格内容换行</label>
                                <p className="text-xs text-slate-500 mt-0.5">关闭后可启用列自动隐藏</p>
                            </div>
                            <button
                                onClick={() => setTableWrapContent(!tableWrapContent)}
                                className={`relative w-11 h-6 rounded-full transition-colors ${tableWrapContent ? 'bg-blue-500' : 'bg-slate-600'}`}
                            >
                                <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${tableWrapContent ? 'left-6' : 'left-1'}`} />
                            </button>
                        </div>
                    </div>

                    {/* Auto-hide columns (only when not wrapping) */}
                    {!tableWrapContent && (
                        <div className="space-y-3 p-3 bg-slate-900/50 rounded-lg">
                            <label className="text-sm font-medium text-slate-300">可自动隐藏的列</label>
                            <p className="text-xs text-slate-500">当空间不足时，这些列会自动隐藏</p>

                            <div className="grid grid-cols-2 gap-2 mt-2">
                                <label className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-slate-700/50 transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={canHideCommand}
                                        onChange={(e) => setCanHideCommand(e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 bg-slate-700"
                                    />
                                    <span className="text-sm text-slate-300">命令</span>
                                </label>

                                <label className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-slate-700/50 transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={canHideDuration}
                                        onChange={(e) => setCanHideDuration(e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 bg-slate-700"
                                    />
                                    <span className="text-sm text-slate-300">耗时</span>
                                </label>

                                <label className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-slate-700/50 transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={canHideActions}
                                        onChange={(e) => setCanHideActions(e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 bg-slate-700"
                                    />
                                    <span className="text-sm text-slate-300">操作</span>
                                </label>

                                <label className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-slate-700/50 transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={canHideNote}
                                        onChange={(e) => setCanHideNote(e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 bg-slate-700"
                                    />
                                    <span className="text-sm text-slate-300">备注</span>
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Always visible columns info */}
                    <div className="p-3 bg-slate-900/50 rounded-lg">
                        <p className="text-xs text-slate-400">
                            <span className="text-emerald-400">永不隐藏：</span> 序号、状态、名称
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-slate-700 bg-slate-900/30">
                    <p className="text-xs text-slate-500 text-center">设置会自动保存到浏览器</p>
                </div>
            </div>
        </div>
    );
}
