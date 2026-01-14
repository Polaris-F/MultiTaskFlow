import { useTaskStore } from '../stores/taskStore';

export function ToastContainer() {
    const { toasts, removeToast } = useTaskStore();

    return (
        <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
            {toasts.map(toast => (
                <div
                    key={toast.id}
                    onClick={() => removeToast(toast.id)}
                    className={`px-4 py-3 rounded-lg shadow-lg text-sm font-medium cursor-pointer animate-in slide-in-from-right-5 fade-in duration-300 ${toast.type === 'success'
                            ? 'bg-emerald-600 text-white'
                            : toast.type === 'error'
                                ? 'bg-red-600 text-white'
                                : 'bg-blue-600 text-white'
                        }`}
                >
                    {toast.message}
                </div>
            ))}
        </div>
    );
}
