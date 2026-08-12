"use client";

import { useState, useEffect, useCallback } from "react";

type ProcessingStage = 
  | "input" 
  | "pattern-analysis" 
  | "memory-retrieval" 
  | "attitude-check"
  | "prompt-generation"
  | "inference"
  | "output-validation"
  | "complete";

type ProcessingLog = {
  readonly id: string;
  readonly timestamp: string;
  readonly userMessage: string;
  readonly stages: ReadonlyArray<{
    readonly stage: ProcessingStage;
    readonly status: "pending" | "active" | "complete" | "error";
    readonly duration?: number;
    readonly data?: unknown;
  }>;
  readonly finalResponse?: string;
};

export function DevProcessingPanel() {
  const [logs, setLogs] = useState<ProcessingLog[]>([]);
  const [selectedLog, setSelectedLog] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Expose global processing logger
  useEffect(() => {
    const win = window as unknown as Record<string, unknown>;
    
    win.shinonStartProcessing = (message: string) => {
      const id = `proc_${Date.now()}`;
      const newLog: ProcessingLog = {
        id,
        timestamp: new Date().toLocaleTimeString(),
        userMessage: message.slice(0, 50) + (message.length > 50 ? "..." : ""),
        stages: [
          { stage: "input", status: "complete" },
          { stage: "pattern-analysis", status: "pending" },
          { stage: "memory-retrieval", status: "pending" },
          { stage: "attitude-check", status: "pending" },
          { stage: "prompt-generation", status: "pending" },
          { stage: "inference", status: "pending" },
          { stage: "output-validation", status: "pending" },
        ],
      };
      setLogs(prev => [newLog, ...prev].slice(0, 20));
      return id;
    };

    win.shinonUpdateStage = (logId: string, stage: ProcessingStage, status: ProcessingLog["stages"][0]["status"], data?: unknown) => {
      setLogs(prev => prev.map(log => {
        if (log.id !== logId) return log;
        return {
          ...log,
          stages: log.stages.map(s => s.stage === stage ? { ...s, status, data } : s),
        };
      }));
    };

    win.shinonCompleteProcessing = (logId: string, response: string) => {
      setLogs(prev => prev.map(log => {
        if (log.id !== logId) return log;
        return {
          ...log,
          stages: log.stages.map(s => s.status === "pending" ? { ...s, status: "complete" as const } : s),
          finalResponse: response.slice(0, 100) + (response.length > 100 ? "..." : ""),
        };
      }));
    };
  }, []);

  const getStageColor = (status: ProcessingLog["stages"][0]["status"]) => {
    switch (status) {
      case "complete": return "bg-green-500";
      case "active": return "bg-blue-500 animate-pulse";
      case "error": return "bg-red-500";
      default: return "bg-gray-600";
    }
  };

  const getStageIcon = (stage: ProcessingStage) => {
    switch (stage) {
      case "input": return "📥";
      case "pattern-analysis": return "🔍";
      case "memory-retrieval": return "💾";
      case "attitude-check": return "🎭";
      case "prompt-generation": return "✍️";
      case "inference": return "🧠";
      case "output-validation": return "✓";
      case "complete": return "✅";
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-24 z-50 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded border border-gray-600"
      >
        [DEV] Processing ({logs.length})
      </button>
    );
  }

  const selectedLogData = logs.find(l => l.id === selectedLog);

  return (
    <div className="fixed bottom-4 right-24 z-50 w-[500px] h-[400px] bg-gray-900 border border-gray-700 rounded-lg shadow-2xl flex flex-col">
      <div className="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-800 rounded-t-lg">
        <span className="text-xs font-semibold text-gray-300">[DEV] Processing Pipeline</span>
        <div className="flex items-center gap-2">
          <button onClick={() => setLogs([])} className="text-xs text-gray-400 hover:text-gray-200">Clear</button>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-gray-200">×</button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Log List */}
        <div className="w-1/2 border-r border-gray-700 overflow-y-auto">
          {logs.map(log => (
            <button
              key={log.id}
              onClick={() => setSelectedLog(log.id)}
              className={`w-full text-left p-2 text-xs border-b border-gray-800 hover:bg-gray-800 ${
                selectedLog === log.id ? "bg-gray-800" : ""
              }`}
            >
              <div className="text-gray-400">{log.timestamp}</div>
              <div className="text-gray-300 truncate">{log.userMessage}</div>
              <div className="flex gap-1 mt-1">
                {log.stages.slice(0, 4).map(s => (
                  <div
                    key={s.stage}
                    className={`w-2 h-2 rounded-full ${getStageColor(s.status)}`}
                    title={s.stage}
                  />
                ))}
              </div>
            </button>
          ))}
          
          {logs.length === 0 && (
            <p className="text-gray-500 text-center py-4 text-xs">
              No processing logs yet.<br />
              Use window.shinonStartProcessing(msg)
            </p>
          )}
        </div>

        {/* Stage Detail */}
        <div className="w-1/2 overflow-y-auto p-3">
          {selectedLogData ? (
            <div className="space-y-2">
              <div className="text-xs text-gray-400 mb-2">Message: {selectedLogData.userMessage}</div>
              
              {selectedLogData.stages.map((stage, i) => (
                <div 
                  key={stage.stage}
                  className={`flex items-center gap-2 p-2 rounded text-xs ${
                    stage.status === "error" ? "bg-red-950/30" :
                    stage.status === "active" ? "bg-blue-950/30" :
                    stage.status === "complete" ? "bg-green-950/30" :
                    "bg-gray-800/50"
                  }`}
                >
                  <span>{getStageIcon(stage.stage)}</span>
                  <div className="flex-1">
                    <div className="font-medium text-gray-300">
                      {stage.stage.replace(/-/g, " ").toUpperCase()}
                    </div>
                    <div className={`text-[10px] ${
                      stage.status === "error" ? "text-red-400" :
                      stage.status === "active" ? "text-blue-400" :
                      stage.status === "complete" ? "text-green-400" :
                      "text-gray-500"
                    }`}>
                      {stage.status}
                    </div>
                  </div>
                </div>
              ))}
              
              {selectedLogData.finalResponse && (
                <div className="mt-3 p-2 bg-gray-800 rounded">
                  <div className="text-xs text-gray-400 mb-1">Response Preview:</div>
                  <div className="text-xs text-gray-300">{selectedLogData.finalResponse}</div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4 text-xs">Select a log to view details</p>
          )}
        </div>
      </div>
    </div>
  );
}
