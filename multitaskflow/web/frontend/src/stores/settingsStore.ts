import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsStore {
    // Settings panel open state
    isSettingsOpen: boolean;

    // Actions
    setSettingsOpen: (open: boolean) => void;
}

export const useSettingsStore = create<SettingsStore>()(
    persist(
        (set) => ({
            isSettingsOpen: false,

            // Actions
            setSettingsOpen: (open) => set({ isSettingsOpen: open }),
        }),
        {
            name: 'multitaskflow-settings',
        }
    )
);
