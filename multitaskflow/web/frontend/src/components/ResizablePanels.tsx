import { useState, useRef, useCallback } from 'react';

interface ResizablePanelsProps {
    leftPanel: React.ReactNode;
    rightPanel: React.ReactNode | null;
    defaultLeftWidth?: number; // percentage
    minLeftWidth?: number; // percentage
    maxLeftWidth?: number; // percentage
}

export function ResizablePanels({
    leftPanel,
    rightPanel,
    defaultLeftWidth = 60,
    minLeftWidth = 30,
    maxLeftWidth = 80
}: ResizablePanelsProps) {
    const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
    const [isDragging, setIsDragging] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);

        const handleMouseMove = (moveEvent: MouseEvent) => {
            if (!containerRef.current) return;

            const rect = containerRef.current.getBoundingClientRect();
            const newWidth = ((moveEvent.clientX - rect.left) / rect.width) * 100;

            // Clamp to min/max
            const clamped = Math.max(minLeftWidth, Math.min(maxLeftWidth, newWidth));
            setLeftWidth(clamped);
        };

        const handleMouseUp = () => {
            setIsDragging(false);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }, [minLeftWidth, maxLeftWidth]);

    // If no right panel, left panel takes full width
    if (!rightPanel) {
        return (
            <div className="flex-1 flex min-h-0">
                {leftPanel}
            </div>
        );
    }

    return (
        <div ref={containerRef} className="flex-1 flex min-h-0 relative">
            {/* Left Panel */}
            <div
                className="overflow-hidden flex flex-col"
                style={{ width: `${leftWidth}%`, minWidth: '200px' }}
            >
                {leftPanel}
            </div>

            {/* Draggable Divider */}
            <div
                className={`w-2 flex-shrink-0 cursor-col-resize group relative
                    ${isDragging ? 'bg-blue-500' : 'bg-slate-700 hover:bg-blue-500'}
                    transition-colors duration-150`}
                onMouseDown={handleMouseDown}
            >
                {/* Visual indicator */}
                <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-1 opacity-50 group-hover:opacity-100">
                    <div className="absolute top-1/2 -translate-y-1/2 left-1/2 -translate-x-1/2 flex flex-col gap-1">
                        <div className="w-1 h-1 bg-white/50 rounded-full" />
                        <div className="w-1 h-1 bg-white/50 rounded-full" />
                        <div className="w-1 h-1 bg-white/50 rounded-full" />
                    </div>
                </div>
            </div>

            {/* Right Panel */}
            <div
                className="overflow-hidden flex flex-col flex-1"
                style={{ minWidth: '250px' }}
            >
                {rightPanel}
            </div>
        </div>
    );
}
