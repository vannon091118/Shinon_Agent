"use client";

import { useState, useEffect } from "react";

type DebugEntry = {
  readonly timestamp: string;
  readonly level: "info" | "warn" | "error" | "debug";
  readonly component: string;
  readonly message: string;
  readonly data?: unknown;
};

export function DevDebugPanel() {
  const [logs, setLogs] = useState<DebugEntry[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Listen for debug events from window
    const handleDebugEvent = (e: Event) => {
      const customEvent = e as CustomEvent<DebugEntry>;
      setLogs(prev => [customEvent.detail, ...prev].slice(0, 100));
    };
    
    window.addEventListener("shinon-debug", handleDebugEvent);
    return () => window.removeEventListener("shinon-debug", handleDebugEvent);
  }, []);

  // Expose global debug function
  useEffect(() => {
    (window as unknown as Record<string, unknown>).shinonDebug = (
      level: DebugEntry["level"],
      component: string,
      message: string,
      data?: unknown
    ) => {
      const entry: DebugEntry = {
        timestamp: new Date().toISOString().split("T")[1].split(".")[0],
        level,
        component,
        message,
        data,
      };
      setLogs(prev => [entry, ...prev].slice(0, 100));
      
      // Also log to console
      console[level](`[${component}] ${message}`, data || "");
    };
  }, []);

  const filteredLogs = filter === "all" 
    ? logs 
    : logs.filter(l => l.level === filter || l.component === filter);

  const components = [...new Set(logs.map(l => l.component))];

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-50 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded border border-gray-600"
      >
        [DEV] Debug
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 h-80 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl flex flex-col">
      <div className="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-800 rounded-t-lg">
        <span className="text-xs font-semibold text-gray-300">[DEV] Debug Output</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{logs.length} entries</span>
          <button onClick={() => setLogs([])} className="text-xs text-gray-400 hover:text-gray-200">Clear</button>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-gray-200">×</button>
        </div>
      </div>
      
      <div className="flex items-center gap-2 p-2 border-b border-gray-700">
        <select 
          value={filter} 
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter logs by component"
          className="bg-gray-800 text-gray-300 text-xs rounded px-2 py-1 border border-gray-600"
        >
          <option value="all">All Components</option>
          {components.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        
        <div className="flex gap-1">
          {(["info", "warn", "error", "debug"] as const).map(level => (
            <button
              key={level}
              onClick={() => setFilter(filter === level ? "all" : level)}
              className={`px-2 py-1 text-xs rounded ${
                filter === level 
                  ? level === "error" ? "bg-red-900 text-red-200" :
                    level === "warn" ? "bg-yellow-900 text-yellow-200" :
                    level === "debug" ? "bg-blue-900 text-blue-200" :
                    "bg-gray-700 text-gray-200"
                  : "bg-gray-800 text-gray-500"
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredLogs.map((log, i) => (
          <div 
            key={i} 
            className={`text-xs p-2 rounded border-l-2 ${
              log.level === "error" ? "bg-red-950/30 border-red-500 text-red-200" :
              log.level === "warn" ? "bg-yellow-950/30 border-yellow-500 text-yellow-200" :
              log.level === "debug" ? "bg-blue-950/30 border-blue-500 text-blue-200" :
              "bg-gray-800/50 border-gray-500 text-gray-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-gray-500">{log.timestamp}</span>
              <span className="text-gray-400">[{log.component}]</span>
              <span className={
                log.level === "error" ? "text-red-400" :
                log.level === "warn" ? "text-yellow-400" :
                log.level === "debug" ? "text-blue-400" :
                "text-gray-300"
              }>{log.level.toUpperCase()}</span>
            </div>
            <div className="mt-1">{log.message}</div>
            {log.data && (
              <pre className="mt-1 p-1 bg-gray-950 rounded text-gray-500 overflow-x-auto">
                {JSON.stringify(log.data, null, 2)}
              </pre>
            )}
          </div>
        ))}
        
        {filteredLogs.length === 0 && (
          <p className="text-gray-500 text-center py-4 text-xs">No logs yet. Use window.shinonDebug(level, component, message, data)</p>
        )}
      </div>
    </div>
  );
}
