import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';

interface XTerminalProps {
    content: string;
    onContentUpdate?: (content: string) => void;
}

export function XTerminal({ content }: XTerminalProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const terminalRef = useRef<HTMLDivElement>(null);
    const xtermRef = useRef<Terminal | null>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);
    const lastContentLengthRef = useRef(0);

    // 初始化终端
    useEffect(() => {
        if (!terminalRef.current || xtermRef.current) return;

        const terminal = new Terminal({
            theme: {
                background: '#0f172a',
                foreground: '#e2e8f0',
                cursor: '#e2e8f0',
                cursorAccent: '#0f172a',
                selectionBackground: '#334155',
                black: '#1e293b',
                red: '#ef4444',
                green: '#22c55e',
                yellow: '#eab308',
                blue: '#3b82f6',
                magenta: '#a855f7',
                cyan: '#06b6d4',
                white: '#f1f5f9',
                brightBlack: '#475569',
                brightRed: '#f87171',
                brightGreen: '#4ade80',
                brightYellow: '#facc15',
                brightBlue: '#60a5fa',
                brightMagenta: '#c084fc',
                brightCyan: '#22d3ee',
                brightWhite: '#ffffff',
            },
            fontSize: 12,
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            cursorBlink: false,
            cursorStyle: 'underline',
            scrollback: 10000,
            convertEol: true,
            disableStdin: true,
        });

        const fitAddon = new FitAddon();
        const webLinksAddon = new WebLinksAddon();

        terminal.loadAddon(fitAddon);
        terminal.loadAddon(webLinksAddon);

        terminal.open(terminalRef.current);

        // 使用 FitAddon 自适应容器大小
        const doFit = () => {
            try {
                fitAddon.fit();
            } catch (e) {
                // 忽略 fit 错误
            }
        };

        // 初始 fit
        setTimeout(doFit, 0);

        xtermRef.current = terminal;
        fitAddonRef.current = fitAddon;

        // 监听窗口大小变化
        const handleResize = () => doFit();
        window.addEventListener('resize', handleResize);

        const resizeObserver = new ResizeObserver(doFit);
        if (containerRef.current) {
            resizeObserver.observe(containerRef.current);
        }

        return () => {
            window.removeEventListener('resize', handleResize);
            resizeObserver.disconnect();
            terminal.dispose();
            xtermRef.current = null;
            fitAddonRef.current = null;
        };
    }, []);

    // 添加左边距的辅助函数
    const addLeftMargin = (text: string): string => {
        // 在每行开头添加2个空格作为左边距
        return text.split('\n').map(line => '  ' + line).join('\n');
    };

    // 写入内容
    useEffect(() => {
        const terminal = xtermRef.current;
        if (!terminal) return;

        if (content.length > lastContentLengthRef.current) {
            const newContent = content.slice(lastContentLengthRef.current);
            terminal.write(addLeftMargin(newContent));
            lastContentLengthRef.current = content.length;
        } else if (content.length < lastContentLengthRef.current) {
            terminal.clear();
            terminal.write(addLeftMargin(content));
            lastContentLengthRef.current = content.length;
        }
    }, [content]);

    return (
        <div
            ref={containerRef}
            className="w-full h-full min-h-[200px]"
            style={{ backgroundColor: '#0f172a' }}
        >
            <div
                ref={terminalRef}
                style={{
                    width: '100%',
                    height: '100%',
                }}
            />
            <style>{`
                .xterm-viewport::-webkit-scrollbar {
                    width: 10px;
                }
                .xterm-viewport::-webkit-scrollbar-track {
                    background: #1e293b;
                }
                .xterm-viewport::-webkit-scrollbar-thumb {
                    background: #475569;
                    border-radius: 5px;
                }
                .xterm-viewport::-webkit-scrollbar-thumb:hover {
                    background: #64748b;
                }
            `}</style>
        </div>
    );
}
