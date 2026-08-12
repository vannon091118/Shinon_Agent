/**
 * Model Scanner API Route
 * Scans local project models/ directory for .gguf files
 */

import { readdir, stat } from "node:fs/promises";
import { join, extname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";

// Get project root directory
const __dirname = fileURLToPath(new URL(".", import.meta.url));
const PROJECT_ROOT = join(__dirname, "..", "..", "..");

export type ModelInfo = {
  readonly id: string;
  readonly name: string;
  readonly filename: string;
  readonly path: string;
  readonly size: number;
  readonly sizeFormatted: string;
  readonly parameters?: string;
  readonly quantization?: string;
  readonly downloaded: boolean;
  readonly required: boolean;
  readonly downloadUrl?: string;
};

export type ModelScanResponse = {
  readonly ok: true;
  readonly models: ReadonlyArray<ModelInfo>;
  readonly requiredMissing: ReadonlyArray<ModelInfo>;
  readonly selectedModel?: ModelInfo;
} | {
  readonly ok: false;
  readonly error: string;
};

const REQUIRED_MODELS = [
  { 
    name: "Qwen 2.5 0.5B", 
    filenamePattern: /qwen.*0\.5b.*\.gguf/i, 
    params: "0.5B", 
    quantization: "Q4_K_M",
    downloadUrl: "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
  },
  { 
    name: "Llama 3.2 1B", 
    filenamePattern: /llama.*3.*1b.*\.gguf/i, 
    params: "1B", 
    quantization: "Q4_K_M",
    downloadUrl: "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
  },
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function extractModelInfo(filename: string): Pick<ModelInfo, "parameters" | "quantization"> {
  const lower = filename.toLowerCase();
  const paramsMatch = lower.match(/(\d+\.?\d*)b/);
  const parameters = paramsMatch ? `${paramsMatch[1]}B` : undefined;
  const quantMatch = lower.match(/(q[\d]+_[kmls]_?[km]?)/);
  const quantization = quantMatch ? quantMatch[1].toUpperCase() : undefined;
  return { parameters, quantization };
}

export async function scanModels(): Promise<ModelScanResponse> {
  try {
    const scanPaths: string[] = [];
    const appData = process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local");
    
    // Scan both local project and APPDATA
    scanPaths.push(
      join(PROJECT_ROOT, "models"),
      join(PROJECT_ROOT, "data", "models"),
      join(appData, "ShinonLLM", "models"),
    );
    
    // DEBUG: Log scan paths
    console.log("[DEBUG] scanModels: Scanning paths:", scanPaths);
    
    const foundModels: ModelInfo[] = [];
    
    for (const scanPath of scanPaths) {
      try {
        // DEBUG: Log each path being scanned
        console.log(`[DEBUG] scanModels: Scanning ${scanPath}...`);
        
        const entries = await readdir(scanPath, { withFileTypes: true });
        
        // DEBUG: Log number of entries found
        console.log(`[DEBUG] scanModels: Found ${entries.length} entries in ${scanPath}`);
        
        for (const entry of entries) {
          if (entry.isFile() && extname(entry.name) === ".gguf") {
            // DEBUG: Log each .gguf file found
            console.log(`[DEBUG] scanModels: Found .gguf file: ${entry.name}`);
            
            const fullPath = join(scanPath, entry.name);
            const stats = await stat(fullPath);
            const { parameters, quantization } = extractModelInfo(entry.name);
            
            // Check if this is a required model
            const requiredMatch = REQUIRED_MODELS.find(r => r.filenamePattern.test(entry.name));
            
            foundModels.push({
              id: `model_${entry.name.replace(/[^a-z0-9]/gi, "_")}`,
              name: requiredMatch?.name || basename(entry.name, ".gguf").replace(/[_-]/g, " "),
              filename: entry.name,
              path: fullPath,
              size: stats.size,
              sizeFormatted: formatBytes(stats.size),
              parameters: requiredMatch?.params || parameters,
              quantization: requiredMatch?.quantization || quantization,
              downloaded: true,
              required: !!requiredMatch,
              downloadUrl: requiredMatch?.downloadUrl,
            });
          }
        }
      } catch (err) {
        // DEBUG: Log why a path was skipped
        console.log(`[DEBUG] scanModels: Skipped ${scanPath} - ${err instanceof Error ? err.message : 'unknown error'}`);
      }
    }
    
    // DEBUG: Log summary
    console.log(`[DEBUG] scanModels: Total models found: ${foundModels.length}`);
    console.log(`[DEBUG] scanModels: Model names: ${foundModels.map(m => m.filename).join(", ")}`);
    
    // Find missing required models
    const requiredMissing: ModelInfo[] = [];
    for (const required of REQUIRED_MODELS) {
      const found = foundModels.some(m => required.filenamePattern.test(m.filename));
      if (!found) {
        requiredMissing.push({
          id: `required_${required.name.replace(/\s+/g, "_").toLowerCase()}`,
          name: required.name,
          filename: `${required.name.replace(/\s+/g, "-").toLowerCase()}.gguf`,
          path: "",
          size: 0,
          sizeFormatted: "Not downloaded",
          parameters: required.params,
          quantization: required.quantization,
          downloaded: false,
          required: true,
          downloadUrl: required.downloadUrl,
        });
      }
    }
    
    // DEBUG: Log missing required models
    console.log(`[DEBUG] scanModels: Missing required models: ${requiredMissing.map(m => m.name).join(", ")}`);
    
    // Select best model (prefer required, smallest first)
    const requiredAvailable = foundModels.filter(m => m.required);
    const selectedModel = requiredAvailable.length > 0 
      ? [...requiredAvailable].sort((a, b) => a.size - b.size)[0]
      : foundModels.length > 0 
        ? [...foundModels].sort((a, b) => a.size - b.size)[0]
        : undefined;
    
    return {
      ok: true,
      models: Object.freeze(foundModels),
      requiredMissing: Object.freeze(requiredMissing),
      selectedModel,
    };
  } catch (error) {
    console.error("[DEBUG] scanModels: Fatal error:", error);
    return {
      ok: false,
      error: error instanceof Error ? error.message : "Failed to scan models",
    };
  }
}
