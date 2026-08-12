import { routeBackendCall } from "../../../inference/src/router/backendRouter.js";
import { extractPattern, type Pattern } from "../../../character/src/experience/patterns.js";
import { 
  queryTier1, 
  queryTier2 
} from "../../../character/src/experience/twoTierMemory.js";
import { 
  getUserAttitudes, 
  updateAttitude 
} from "../../../memory/src/adapters/sqliteAdapter.js";

export type ChatRole = "system" | "user" | "assistant";

export type ChatHistoryEntry = Readonly<{
  role: ChatRole;
  content: string;
}>;

export type OrchestrateTurnInput = Readonly<{
  request?: Readonly<{
    sessionId?: string;
    conversationId?: string;
    requestId?: string;
  }>;
  userText: string;
  history: ReadonlyArray<ChatHistoryEntry>;
  memoryContext: Readonly<Record<string, unknown>>;
}>;

export type OrchestrateTurnOutput = Readonly<{
  reply: string;
  message: Readonly<{
    role: "assistant";
    content: string;
  }>;
  source: "orchestrator";
  model: string;
  prompt: string;
  guardrailStatus: "validated";
}>;

type OrchestrateTurnErrorCode = "BAD_REQUEST" | "ORCHESTRATION_FAILED" | "INTERNAL_SERVER_ERROR";

type OrchestrateTurnError = Readonly<{
  code: OrchestrateTurnErrorCode;
  message: string;
}>;

type PromptBundle = Readonly<{
  prompt: string;
  memorySummary: string;
  runtimePlan: Readonly<{
    intent: "question" | "analysis" | "code" | "summary";
    nextAction: "answer" | "explain" | "propose_patch" | "summarize";
    userStyle: "neutral" | "aggressive" | "cheerful" | "impatient" | "thoughtful";
  }>;
  // NEW: Character context from runtime thinking
  characterContext?: Readonly<{
    patterns: Pattern[];
    facts: string[];
    attitudes: AttitudeState | null;
    confront: boolean;
    toneDirective: string;
  }>;
}>;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function failClosed(code: OrchestrateTurnErrorCode, message: string): never {
  throw { code, message } satisfies OrchestrateTurnError;
}

function sortKeys(value: Record<string, unknown>): string[] {
  return Object.keys(value).sort((left, right) => left.localeCompare(right));
}

function stableSerialize(value: unknown, seen: WeakSet<object>): string {
  if (value === null) {
    return "null";
  }

  const type = typeof value;
  if (type === "string") {
    return JSON.stringify(value);
  }
  if (type === "number" || type === "boolean") {
    return String(value);
  }
  if (type === "bigint") {
    return JSON.stringify((value as bigint).toString());
  }
  if (type === "undefined" || type === "function" || type === "symbol") {
    return JSON.stringify(String(value));
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableSerialize(entry, seen)).join(",")}]`;
  }

  if (!isPlainObject(value)) {
    return JSON.stringify(String(value));
  }

  if (seen.has(value)) {
    failClosed("BAD_REQUEST", "memoryContext contains a circular reference");
  }

  seen.add(value);
  const parts = sortKeys(value).map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key], seen)}`);
  seen.delete(value);
  return `{${parts.join(",")}}`;
}

function normalizeInput(input: OrchestrateTurnInput): OrchestrateTurnInput {
  if (!isPlainObject(input)) {
    failClosed("BAD_REQUEST", "orchestrateTurn input must be an object");
  }

  if (!isNonEmptyString(input.userText)) {
    failClosed("BAD_REQUEST", "orchestrateTurn requires a non-empty userText");
  }

  if (!Array.isArray(input.history)) {
    failClosed("BAD_REQUEST", "orchestrateTurn requires a history array");
  }

  for (const entry of input.history) {
    if (!isPlainObject(entry)) {
      failClosed("BAD_REQUEST", "history entries must be plain objects");
    }
    if (entry.role !== "system" && entry.role !== "user" && entry.role !== "assistant") {
      failClosed("BAD_REQUEST", "history entry role is invalid");
    }
    if (!isNonEmptyString(entry.content)) {
      failClosed("BAD_REQUEST", "history entry content must be a non-empty string");
    }
  }

  if (!isPlainObject(input.memoryContext)) {
    failClosed("BAD_REQUEST", "memoryContext must be a plain object");
  }

  return {
    request: input.request,
    userText: input.userText.trim(),
    history: Object.freeze(
      input.history.map((entry) =>
        Object.freeze({
          role: entry.role,
          content: entry.content.trim(),
        }),
      ),
    ),
    memoryContext: Object.freeze({ ...input.memoryContext }),
  };
}

function summarizeMemory(memoryContext: Readonly<Record<string, unknown>>): string {
  const entries = sortKeys(memoryContext).map((key) => `${key}=${stableSerialize(memoryContext[key], new WeakSet<object>())}`);
  return entries.join(" | ");
}

/**
 * Derives a runtime plan (intent, nextAction, and userStyle) from the user's text and conversation history.
 *
 * @param input - The orchestrate turn input whose `userText` and `history` are analyzed to infer intent and user tone.
 * @returns The chosen runtime plan: an object with `intent` (`"code" | "summary" | "analysis" | "question"`), `nextAction` (`"propose_patch" | "summarize" | "explain" | "answer"`), and `userStyle` (`"neutral" | "aggressive" | "cheerful" | "impatient" | "thoughtful"`).
 */
function buildRuntimePlan(input: OrchestrateTurnInput): PromptBundle["runtimePlan"] {
  const text = `${input.userText} ${input.history.map((entry) => entry.content).join(" ")}`.toLowerCase();
  
  let userStyle: PromptBundle["runtimePlan"]["userStyle"] = "neutral";
  if (/(fuck|scheiß|verdammt|idiot|digga|rotze|garbage|shit)/u.test(text)) {
    userStyle = "aggressive";
  } else if (/(schnell|now|sofort|asap|hurry|beeil)/u.test(text)) {
    userStyle = "impatient";
  } else if (/(haha|lol|lmao|geil|nice|cool|\^\^|:d)/u.test(text)) {
    userStyle = "cheerful";
  } else if (/(glaubst du|denkst du|warum|wieso|philosoph|sinn)/u.test(text)) {
    userStyle = "thoughtful";
  }

  if (/(code|bug|error|typescript|javascript|python|sql|patch)/u.test(text)) {
    return Object.freeze({ intent: "code", nextAction: "propose_patch", userStyle });
  }
  if (/(summarize|summary|zusammenfass|tl;dr|tldr)/u.test(text)) {
    return Object.freeze({ intent: "summary", nextAction: "summarize", userStyle });
  }
  if (/(analy|compare|bewert|audit|review)/u.test(text)) {
    return Object.freeze({ intent: "analysis", nextAction: "explain", userStyle });
  }
  return Object.freeze({ intent: "question", nextAction: "answer", userStyle });
}

// ============================================================================
// CHARACTER RUNTIME INTEGRATION (0.3.0)
// Implements: Pattern Engine → Two-Tier Memory → Attitude Tracker → Prompt
// ============================================================================

/**
 * Extract patterns from user input using Pattern Engine.
 * Step 2 in ARCHITECTURE: Pattern Check (Tier 2)
 * NOTE: Stub implementation - Pattern Engine expects PersonalFact objects
 */
function extractPatternsFromInput(userText: string): Pattern[] {
  // TODO: Convert userText to PersonalFact and extract patterns
  // For now, return empty array as stub
  return [];
}

/**
 * Query Two-Tier Memory system.
 * Step 1 & 2 in ARCHITECTURE: Hot Zone (Tier 1) + Pattern Check (Tier 2)
 * NOTE: Stub implementation - requires SQLite adapter
 */
async function queryCharacterMemory(
  _sessionId: string,
  _userText: string,
): Promise<{ facts: string[]; patterns: Pattern[] }> {
  // TODO: Implement with actual SQLite adapter
  // For now, return empty results as stub
  return { facts: [], patterns: [] };
}

/**
 * Load and evaluate attitudes for user.
 * Step 3 in ARCHITECTURE: Attitude Check (-10 to +10)
 * NOTE: Stub implementation - requires SQLite adapter
 */
async function evaluateAttitudes(
  _userId: string,
  _newPatterns: Pattern[],
): Promise<{ attitudes: AttitudeState | null; shouldConfront: boolean; toneDirective: string }> {
  // TODO: Load from SQLite and apply rules
  // For now, return neutral state as stub
  return { 
    attitudes: null, 
    shouldConfront: false, 
    toneDirective: "NORMAL_INTERACTION: Match user sentiment." 
  };
}

/**
 * Build character-aware prompt with all runtime context.
 * Step 5 in ARCHITECTURE: Prompt Generator
 */
function buildCharacterPrompt(
  input: OrchestrateTurnInput,
  characterContext: PromptBundle["characterContext"],
): PromptBundle {
  const normalized = normalizeInput(input);
  const historyBlock = normalized.history.length
    ? normalized.history
        .map((entry) => `${entry.role.toUpperCase()}: ${entry.content}`)
        .join("\n")
    : "HISTORY: <empty>";
  
  const runtimePlan = buildRuntimePlan(normalized);
  
  // Build character context block
  let characterBlock = "";
  if (characterContext) {
    const patternsText = characterContext.patterns.length > 0
      ? `RECOGNIZED_PATTERNS: ${characterContext.patterns.map(p => `${p.type} (${p.confidence.toFixed(2)}): ${p.anchor}`).join("; ")}`
      : "RECOGNIZED_PATTERNS: none";
    
    const factsText = characterContext.facts.length > 0
      ? `KNOWN_FACTS: ${characterContext.facts.join("; ")}`
      : "KNOWN_FACTS: none";
    
    const confrontText = characterContext.confront
      ? "MODE: CONFRONTATION - User shows concerning inconsistency."
      : "MODE: NORMAL";
    
    characterBlock = [
      patternsText,
      factsText,
      confrontText,
      `TONE_DIRECTIVE: ${characterContext.toneDirective}`,
    ].join("\n");
  }
  
  const prompt = [
    "SYSTEM: You are Shinon, a character with memory and attitudes. You develop opinions based on observed patterns. State your thoughts in first person.",
    "",
    characterBlock,
    "",
    `PLAN: intent=${runtimePlan.intent} next_action=${runtimePlan.nextAction} user_style=${runtimePlan.userStyle}`,
    `USER: ${normalized.userText}`,
    historyBlock,
  ].join("\n");

  return Object.freeze({
    prompt,
    memorySummary: characterBlock,
    runtimePlan,
    characterContext,
  });
}

/**
 * Constructs the prompt bundle used by the orchestrator for a single turn.
 *
 * The returned bundle contains a ready-to-send `prompt` string (including a system instruction, a `PLAN:` line with `intent`, `next_action`, and `user_style`, a `USER:` line, a `HISTORY` block, and a `MEMORY` block), a deterministic `memorySummary`, and the computed `runtimePlan`.
 *
 * @param input - The raw orchestration input containing `userText`, `history`, and `memoryContext`; the function normalizes this input before building the bundle.
 * @returns An immutable PromptBundle with `prompt` (string), `memorySummary` (string), and `runtimePlan` (object including `intent`, `nextAction`, and `userStyle`).
 */
function buildPrompt(input: OrchestrateTurnInput): PromptBundle {
  const normalized = normalizeInput(input);
  const historyBlock = normalized.history.length
    ? normalized.history
        .map((entry) => `${entry.role.toUpperCase()}: ${entry.content}`)
        .join("\n")
    : "HISTORY: <empty>";
  const memorySummary = summarizeMemory(normalized.memoryContext);
  const runtimePlan = buildRuntimePlan(normalized);
  const prompt = [
    "SYSTEM: Produce a concise, valid assistant response. Your name is Shinon. Adapt your tone to mirror the user's sentiment as scored below.",
    `PLAN: intent=${runtimePlan.intent} next_action=${runtimePlan.nextAction} user_style=${runtimePlan.userStyle}`,
    `USER: ${normalized.userText}`,
    historyBlock,
    memorySummary.length > 0 ? `MEMORY: ${memorySummary}` : "MEMORY: <empty>",
  ].join("\n");

  return Object.freeze({
    prompt,
    memorySummary,
    runtimePlan,
  });
}

function resolveBackend(memoryContext: Readonly<Record<string, unknown>>): "ollama" | "llamacpp" {
  const backend = typeof memoryContext.backend === "string" ? memoryContext.backend.trim() : "";
  if (backend === "ollama" || backend === "llamacpp") {
    return backend;
  }
  return "llamacpp";
}

function resolveFallbackBackend(
  backend: "ollama" | "llamacpp",
  memoryContext: Readonly<Record<string, unknown>>,
): "ollama" | "llamacpp" {
  const fallback = typeof memoryContext.fallbackBackend === "string" ? memoryContext.fallbackBackend.trim() : "";
  if (fallback === "ollama" || fallback === "llamacpp") {
    return fallback;
  }
  return backend === "llamacpp" ? "ollama" : "llamacpp";
}

function resolveModel(memoryContext: Readonly<Record<string, unknown>>, prompt: string): string {
  const modelHint = typeof memoryContext.modelHint === "string" ? memoryContext.modelHint.trim() : "";
  if (modelHint.length > 0) {
    return modelHint;
  }
  return prompt.length > 1800 ? "orchestrator-long" : "orchestrator-default";
}

function applyGuardrails(input: OrchestrateTurnInput, output: {
  reply: string;
  model: string;
  prompt: string;
}): OrchestrateTurnOutput {
  const normalized = normalizeInput(input);

  if (!isNonEmptyString(output.model)) {
    failClosed("ORCHESTRATION_FAILED", "model output requires a model identifier");
  }
  if (!isNonEmptyString(output.prompt)) {
    failClosed("ORCHESTRATION_FAILED", "model output requires a prompt");
  }
  if (!isNonEmptyString(output.reply)) {
    failClosed("ORCHESTRATION_FAILED", "model output requires a non-empty reply");
  }

  const reply = output.reply.trim();
  if (reply.length === 0 || normalized.userText.length === 0) {
    failClosed("ORCHESTRATION_FAILED", "assistant payload is not valid");
  }

  return Object.freeze({
    reply,
    message: Object.freeze({
      role: "assistant",
      content: reply,
    }),
    source: "orchestrator",
    model: output.model.trim(),
    prompt: output.prompt,
    guardrailStatus: "validated",
  });
}

export async function orchestrateTurn(input: OrchestrateTurnInput): Promise<OrchestrateTurnOutput> {
  try {
    const normalized = normalizeInput(input);
    const sessionId = normalized.request?.sessionId ?? "default";
    const userId = normalized.request?.conversationId ?? "default";
    
    // [NEW] Step 2: Extract patterns from user input
    const newPatterns = extractPatternsFromInput(normalized.userText);
    
    // [NEW] Step 1 & 2: Query Two-Tier Memory (Hot Zone + Tier 2)
    const memoryResults = await queryCharacterMemory(sessionId, normalized.userText);
    
    // [NEW] Step 3: Evaluate attitudes
    const attitudeResults = await evaluateAttitudes(userId, newPatterns);
    
    // [NEW] Step 5: Build character-aware prompt
    const characterContext = Object.freeze({
      patterns: [...memoryResults.patterns, ...newPatterns],
      facts: memoryResults.facts,
      attitudes: attitudeResults.attitudes,
      confront: attitudeResults.shouldConfront,
      toneDirective: attitudeResults.toneDirective,
    });
    
    const promptBundle = buildCharacterPrompt(normalized, characterContext);

    const backend = resolveBackend(normalized.memoryContext);
    const fallbackBackend = resolveFallbackBackend(backend, normalized.memoryContext);
    const model = resolveModel(normalized.memoryContext, promptBundle.prompt);
    const allowFallback = normalized.memoryContext.allowFallback !== false;

    const routed = await routeBackendCall(
      Object.freeze({
        backend,
        fallbackBackend,
        allowFallback,
        model,
        requestId: normalized.request?.requestId,
        sessionId: normalized.request?.sessionId,
        conversationId: normalized.request?.conversationId,
        options: Object.freeze({
          live: true,
          runtimePlan: promptBundle.runtimePlan,
          characterContext: promptBundle.characterContext,
        }),
      }),
      Object.freeze({
        userText: normalized.userText,
        messages: [
          ...normalized.history,
          {
            role: "user",
            content: normalized.userText,
          },
        ],
        requestId: normalized.request?.requestId,
        sessionId: normalized.request?.sessionId,
        conversationId: normalized.request?.conversationId,
      }),
    );

    return applyGuardrails(normalized, {
      reply: routed.content,
      model: routed.model,
      prompt: promptBundle.prompt,
    });
  } catch (error) {
    if (isPlainObject(error) && typeof error.code === "string" && typeof error.message === "string") {
      if (
        error.code === "BAD_REQUEST" ||
        error.code === "ORCHESTRATION_FAILED" ||
        error.code === "INTERNAL_SERVER_ERROR"
      ) {
        throw error;
      }
      throw {
        code: "ORCHESTRATION_FAILED",
        message: "inference routing failed",
      } satisfies OrchestrateTurnError;
    }
    failClosed("INTERNAL_SERVER_ERROR", "orchestrateTurn failed");
  }
}
