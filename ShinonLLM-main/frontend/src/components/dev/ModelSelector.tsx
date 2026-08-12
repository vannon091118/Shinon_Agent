"use client";

import { useState, useEffect } from "react";

export type ModelInfo = {
  readonly id: string;
  readonly name: string;
  readonly filename: string;
  readonly sizeFormatted: string;
  readonly parameters?: string;
  readonly quantization?: string;
  readonly downloaded: boolean;
  readonly required: boolean;
  readonly downloadUrl?: string;
};

type ModelSelectorProps = {
  readonly onModelSelect?: (model: ModelInfo) => void;
  readonly onModelsLoaded?: (models: ModelInfo[]) => void;
  readonly selectedModelId?: string;
};

export function ModelSelector({ onModelSelect, onModelsLoaded, selectedModelId }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [missing, setMissing] = useState<ModelInfo[]>([]);
  const [selected, setSelected] = useState<string>(selectedModelId || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const res = await fetch("/api/models");
      const data = await res.json();
      
      if (data.ok) {
        const loadedModels = [...data.models];
        setModels(loadedModels);
        setMissing([...data.requiredMissing]);
        // Notify parent of all loaded models
        onModelsLoaded?.(loadedModels);
        if (data.selectedModel && !selected) {
          setSelected(data.selectedModel.id);
          onModelSelect?.(data.selectedModel);
        }
      } else {
        // Handle both string errors and object errors with {code, message}
        const errorMessage = typeof data.error === "string" 
          ? data.error 
          : typeof data.error?.message === "string" 
            ? data.error.message 
            : "Failed to load models";
        setError(errorMessage);
        // [DEV] Send to DevDebugPanel
        const win = window as unknown as Record<string, unknown>;
        if (typeof win.shinonDebug === "function") {
          (win.shinonDebug as (level: string, component: string, message: string) => void)(
            "error", 
            "ModelSelector", 
            errorMessage
          );
        }
      }
    } catch (e) {
      setError("Network error");
      // [DEV] Send to DevDebugPanel
      const win = window as unknown as Record<string, unknown>;
      if (typeof win.shinonDebug === "function") {
        (win.shinonDebug as (level: string, component: string, message: string) => void)(
          "error", 
          "ModelSelector", 
          "Network error"
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (model: ModelInfo) => {
    setSelected(model.id);
    onModelSelect?.(model);
  };

  if (loading) return <div className="p-4 text-sm text-gray-500">[DEV] Loading models...</div>;
  if (error) return <div className="p-4 text-sm text-red-500">[DEV] Error: {error}</div>;

  return (
    <div className="border border-gray-700 bg-gray-900 rounded p-4 text-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-200">[DEV] Model Selection</h3>
        <span className="text-xs text-gray-500">{models.length} available, {missing.length} required</span>
      </div>

      {missing.length > 0 && (
        <div className="mb-4 p-3 bg-red-950/50 border border-red-800 rounded">
          <p className="text-red-400 font-medium mb-2">⚠️ Required Models Missing:</p>
          <ul className="space-y-2">
            {missing.map(m => (
              <li key={m.id} className="flex items-center justify-between">
                <span className="text-gray-300">{m.name} ({m.parameters})</span>
                {m.downloadUrl && (
                  <a 
                    href={m.downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded"
                  >
                    Download
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-2 max-h-48 overflow-y-auto">
        {models.map(model => (
          <button
            key={model.id}
            onClick={() => handleSelect(model)}
            className={`w-full text-left p-2 rounded border transition-colors ${
              selected === model.id 
                ? "border-blue-500 bg-blue-950/30" 
                : "border-gray-700 hover:border-gray-600"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`font-medium ${selected === model.id ? "text-blue-400" : "text-gray-200"}`}>
                {model.name}
                {model.required && <span className="ml-2 text-xs text-green-500">✓ Required</span>}
              </span>
              <span className="text-xs text-gray-500">{model.sizeFormatted}</span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              {model.parameters && <span>{model.parameters}</span>}
              {model.quantization && <span>{model.quantization}</span>}
              <span className="text-gray-600">{model.filename}</span>
            </div>
          </button>
        ))}
      </div>

      {models.length === 0 && (
        <p className="text-gray-500 text-center py-4">No models found. Check %APPDATA%/ShinonLLM/models</p>
      )}
    </div>
  );
}
