import { useState, useEffect } from 'react';
import { useSettingsStore } from '../stores/settingsStore';

export function SettingsPanel() {
    const { isSettingsOpen, setSettingsOpen } = useSettingsStore();

    // 通知设置状态
    const [pushplusToken, setPushplusToken] = useState('');
    const [hasEnvToken, setHasEnvToken] = useState(false);
    const [notificationEnabled, setNotificationEnabled] = useState(true);
    const [notificationSaving, setNotificationSaving] = useState(false);
    const [testSending, setTestSending] = useState(false);
    const [notificationMessage, setNotificationMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    // 加载通知设置
    useEffect(() => {
        if (isSettingsOpen) {
            fetch('/api/settings/notification')
                .then(res => res.json())
                .then(data => {
                    setPushplusToken(data.pushplus_token || '');
                    setHasEnvToken(data.has_env_token || false);
                    setNotificationEnabled(data.enabled !== false);
                })
                .catch(() => { });
        }
    }, [isSettingsOpen]);

    // 保存通知设置
    const saveNotificationSettings = async () => {
        setNotificationSaving(true);
        setNotificationMessage(null);
        try {
            const res = await fetch('/api/settings/notification', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pushplus_token: pushplusToken,
                    enabled: notificationEnabled,
                })
            });
            const data = await res.json();
            if (data.success) {
                setNotificationMessage({ type: 'success', text: '设置已保存' });
            } else {
                setNotificationMessage({ type: 'error', text: data.message || '保存失败' });
            }
        } catch (e) {
            setNotificationMessage({ type: 'error', text: '保存失败' });
        }
        setNotificationSaving(false);
    };

    // 发送测试通知
    const sendTestNotification = async () => {
        setTestSending(true);
        setNotificationMessage(null);
        try {
            const res = await fetch('/api/settings/notification/test', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                setNotificationMessage({ type: 'success', text: '测试通知已发送' });
            } else {
                setNotificationMessage({ type: 'error', text: data.message || '发送失败' });
            }
        } catch (e) {
            setNotificationMessage({ type: 'error', text: '发送失败' });
        }
        setTestSending(false);
    };

    if (!isSettingsOpen) return null;

    return (
        <div data-mtf-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSettingsOpen(false)}>
            <div
                className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-slate-700 max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 sticky top-0 bg-slate-800">
                    <h2 className="text-lg font-semibold text-slate-100">⚙️ 设置</h2>
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
                    {/* 通知设置 */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                            📱 消息通知
                        </h3>
                        <p className="text-xs text-slate-500">任务完成或失败时推送通知到微信</p>

                        <div className="flex items-center justify-between rounded-lg bg-slate-900/40 border border-slate-700 px-3 py-2">
                            <div>
                                <p className="text-sm text-slate-200">启用通知</p>
                                <p className="text-xs text-slate-500">关闭后不再发送任务通知</p>
                            </div>
                            <button
                                onClick={() => setNotificationEnabled(!notificationEnabled)}
                                className={`relative w-11 h-6 rounded-full transition-colors ${notificationEnabled ? 'bg-blue-500' : 'bg-slate-600'}`}
                            >
                                <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${notificationEnabled ? 'left-6' : 'left-1'}`} />
                            </button>
                        </div>

                        {hasEnvToken && (
                            <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-400">
                                ✓ 已检测到环境变量 MSG_PUSH_TOKEN
                            </div>
                        )}

                        <div className="space-y-2">
                            <label className="text-xs text-slate-400">PushPlus Token（优先于环境变量）</label>
                            <input
                                type="password"
                                value={pushplusToken}
                                onChange={(e) => setPushplusToken(e.target.value)}
                                placeholder="留空则使用环境变量"
                                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                            />
                            <p className="text-xs text-slate-500">
                                获取 Token: <a href="https://www.pushplus.plus" target="_blank" rel="noopener" className="text-blue-400 hover:underline">pushplus.plus</a>
                            </p>
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={saveNotificationSettings}
                                disabled={notificationSaving}
                                className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white text-sm rounded-lg transition-colors"
                            >
                                {notificationSaving ? '保存中...' : '保存设置'}
                            </button>
                            <button
                                onClick={sendTestNotification}
                                disabled={testSending}
                                className="px-3 py-2 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-700 text-white text-sm rounded-lg transition-colors"
                            >
                                {testSending ? '发送中...' : '发送测试'}
                            </button>
                        </div>

                        {notificationMessage && (
                            <div className={`p-2 rounded-lg text-xs ${notificationMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                                {notificationMessage.text}
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-slate-700 bg-slate-900/30">
                    <p className="text-xs text-slate-500 text-center">通知设置保存到工作区</p>
                </div>
            </div>
        </div>
    );
}
