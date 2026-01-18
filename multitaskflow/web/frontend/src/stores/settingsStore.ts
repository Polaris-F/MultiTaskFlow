import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsStore {
    // Task name column minimum width (percentage)
    taskNameMinWidth: number;

    // Table content wrapping mode
    tableWrapContent: boolean; // true = wrap, false = may auto-hide columns

    // Columns that can be auto-hidden when space is limited (only when tableWrapContent is false)
    // Always visible: order, status, name (name uses taskNameMinWidth)
    canHideCommand: boolean;
    canHideDuration: boolean;
    canHideActions: boolean;
    canHideNote: boolean;

    // Settings panel open state
    isSettingsOpen: boolean;

    // Actions
    setTaskNameMinWidth: (value: number) => void;
    setTableWrapContent: (value: boolean) => void;
    setCanHideCommand: (value: boolean) => void;
    setCanHideDuration: (value: boolean) => void;
    setCanHideActions: (value: boolean) => void;
    setCanHideNote: (value: boolean) => void;
    setSettingsOpen: (open: boolean) => void;
}

export const useSettingsStore = create<SettingsStore>()(
    persist(
        (set) => ({
            // Default values
            taskNameMinWidth: 15, // 15% minimum width for task name column
            tableWrapContent: true, // Default: wrap content
            canHideCommand: true,
            canHideDuration: true,
            canHideActions: false, // Keep actions visible by default
            canHideNote: true,
            isSettingsOpen: false,

            // Actions
            setTaskNameMinWidth: (value) => set({ taskNameMinWidth: value }),
            setTableWrapContent: (value) => set({ tableWrapContent: value }),
            setCanHideCommand: (value) => set({ canHideCommand: value }),
            setCanHideDuration: (value) => set({ canHideDuration: value }),
            setCanHideActions: (value) => set({ canHideActions: value }),
            setCanHideNote: (value) => set({ canHideNote: value }),
            setSettingsOpen: (open) => set({ isSettingsOpen: open }),
        }),
        {
            name: 'multitaskflow-settings',
        }
    )
);
