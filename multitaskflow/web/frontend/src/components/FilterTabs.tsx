

type FilterType = 'all' | 'running' | 'pending' | 'completed' | 'failed' | 'stopped';

const FILTERS: { key: FilterType; label: string }[] = [
    { key: 'all', label: '全部' },
    { key: 'running', label: '运行中' },
    { key: 'pending', label: '等待中' },
    { key: 'completed', label: '已完成' },
    { key: 'failed', label: '失败' },
    { key: 'stopped', label: '已停止' },
];

interface FilterTabsProps {
    current: FilterType;
    onChange: (filter: FilterType) => void;
    counts: Record<FilterType, number>;
}

export function FilterTabs({ current, onChange, counts }: FilterTabsProps) {
    return (
        <div className="flex items-center gap-1 bg-slate-800/60 rounded-lg p-1">
            {FILTERS.map(({ key, label }) => {
                const isActive = current === key;
                const count = counts[key];

                return (
                    <button
                        key={key}
                        onClick={() => onChange(key)}
                        className={`
                            px-4 py-2 rounded-md text-sm font-medium transition-all duration-200
                            ${isActive
                                ? 'bg-blue-600/80 text-white border border-blue-500/50 shadow-lg shadow-blue-500/20'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                            }
                        `}
                    >
                        {label}
                        {count > 0 && (
                            <span className={`ml-1.5 text-xs ${isActive ? 'text-blue-200' : 'text-slate-500'}`}>
                                {count}
                            </span>
                        )}
                    </button>
                );
            })}
        </div>
    );
}

export type { FilterType };
