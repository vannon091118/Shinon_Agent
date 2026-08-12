export type ChatRole = "system" | "user" | "assistant";

export type NormalizedChatTurn = Readonly<{
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  userText: string;
  history: ReadonlyArray<Readonly<{
    role: ChatRole;
    content: string;
  }>>;
}>;

export type BackendName = "primary" | "secondary" | "local";
export type TaskClass = "chat" | "analysis" | "code" | "summarization";
export type BackendHealthState = "healthy" | "degraded" | "unhealthy";

export type RouteModelPolicy = Readonly<{
  id?: string;
  defaultBackend?: BackendName;
  allowDegraded?: boolean;
  backendOrder?: Partial<Record<TaskClass, ReadonlyArray<BackendName>>>;
  taskBackendOverrides?: Partial<Record<TaskClass, BackendName>>;
}>;

export type RouteModelHealth = Readonly<Partial<Record<BackendName, BackendHealthState | boolean>>>;

export type RouteModelInput = Readonly<{
  turn: NormalizedChatTurn;
  memoryContext: Readonly<{
    taskClass?: TaskClass | string;
    modelPolicy?: RouteModelPolicy;
    backendHealth?: RouteModelHealth;
    slot?: string;
  }> & Record<string, unknown>;
}>;

export type ValidatedAssistantPayload = Readonly<{
  role: "assistant";
  content: string;
  model: string;
  backend: BackendName;
  slot: string;
  taskClass: TaskClass;
  validated: true;
  metadata: Readonly<{
    policyId: string;
    healthStatus: BackendHealthState;
    sessionId?: string;
    conversationId?: string;
    requestId?: string;
    historyDepth: number;
  }>;
}>;

type PlainObject = Record<string, unknown>;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeTaskClass(value: unknown): TaskClass | null {
  if (value === "chat" || value === "analysis" || value === "code" || value === "summarization") {
    return value;
  }
  return null;
}

function assertPlainObject(value: unknown, label: string): asserts value is PlainObject {
  if (!isPlainObject(value)) {
    throw new Error(`MODEL_ROUTING_CONTRACT_VIOLATION: ${label} must be a plain object`);
  }
}

function assertNonEmptyOptionalString(value: unknown, label: string): string | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (!isNonEmptyString(value)) {
    throw new Error(`MODEL_ROUTING_CONTRACT_VIOLATION: ${label} must be a non-empty string`);
  }
  return value.trim();
}

function inferTaskClass(turn: NormalizedChatTurn, memoryContext: RouteModelInput["memoryContext"]): TaskClass {
  const explicitTaskClass = normalizeTaskClass(memoryContext.taskClass);
  if (explicitTaskClass) {
    return explicitTaskClass;
  }

  const text = `${turn.userText} ${turn.history.map((entry) => entry.content).join(" ")}`.toLowerCase();
  if (/(code|bug|error|stack|typescript|javascript|python|sql|api)/u.test(text)) {
    return "code";
  }
  if (/(summarize|summary|zusammenfassen|tl;dr|tldr)/u.test(text)) {
    return "summarization";
  }
  if (/(analyze|analysis|review|compare|bewerte|bewerten)/u.test(text)) {
    return "analysis";
  }
  return "chat";
}

function normalizeBackend(value: unknown): BackendName | null {
  if (value === "primary" || value === "secondary" || value === "local") {
    return value;
  }
  return null;
}

function normalizeHealthState(value: unknown): BackendHealthState {
  if (value === true) {
    return "healthy";
  }
  if (value === false) {
    return "unhealthy";
  }
  if (value === "healthy" || value === "degraded" || value === "unhealthy") {
    return value;
  }
  return "unhealthy";
}

function defaultBackendOrder(taskClass: TaskClass): ReadonlyArray<BackendName> {
  switch (taskClass) {
    case "code":
      return ["primary", "secondary", "local"];
    case "analysis":
      return ["primary", "local", "secondary"];
    case "summarization":
      return ["secondary", "primary", "local"];
    case "chat":
    default:
      return ["primary", "secondary", "local"];
  }
}

function resolveBackendOrder(
  taskClass: TaskClass,
  policy: RouteModelPolicy
): ReadonlyArray<BackendName> {
  const override = policy.taskBackendOverrides?.[taskClass];
  if (override) {
    return [override];
  }

  const configuredOrder = policy.backendOrder?.[taskClass];
  if (configuredOrder && configuredOrder.length > 0) {
    const normalized = configuredOrder
      .map((candidate) => normalizeBackend(candidate))
      .filter((candidate): candidate is BackendName => candidate !== null);
    if (normalized.length > 0) {
      return normalized;
    }
  }

  return defaultBackendOrder(taskClass);
}

function readPolicy(memoryContext: RouteModelInput["memoryContext"]): RouteModelPolicy {
  const candidate = memoryContext.modelPolicy;
  if (!isPlainObject(candidate)) {
    return {};
  }

  return {
    id: isNonEmptyString(candidate.id) ? candidate.id.trim() : undefined,
    defaultBackend: normalizeBackend(candidate.defaultBackend),
    allowDegraded: candidate.allowDegraded === true,
    backendOrder: isPlainObject(candidate.backendOrder)
      ? (Object.fromEntries(
          Object.entries(candidate.backendOrder).map(([key, value]) => [
            key,
            Array.isArray(value)
              ? value.map((entry) => normalizeBackend(entry)).filter((entry): entry is BackendName => entry !== null)
              : [],
          ]),
        ) as Partial<Record<TaskClass, ReadonlyArray<BackendName>>>)
      : undefined,
    taskBackendOverrides: isPlainObject(candidate.taskBackendOverrides)
      ? (Object.fromEntries(
          Object.entries(candidate.taskBackendOverrides).map(([key, value]) => [
            key,
            normalizeBackend(value),
          ]),
        ) as Partial<Record<TaskClass, BackendName>>)
      : undefined,
  };
}

function readHealthState(
  backend: BackendName,
  health: RouteModelHealth | undefined,
  allowDegraded: boolean
): BackendHealthState | null {
  const state = normalizeHealthState(health?.[backend]);
  if (state === "healthy") {
    return "healthy";
  }
  if (state === "degraded" && allowDegraded) {
    return "degraded";
  }
  return null;
}

function selectBackend(
  taskClass: TaskClass,
  policy: RouteModelPolicy,
  health: RouteModelHealth | undefined
): { backend: BackendName; healthStatus: BackendHealthState } {
  const candidates = resolveBackendOrder(taskClass, policy);
  const allowDegraded = policy.allowDegraded === true;

  for (const backend of candidates) {
    const healthStatus = readHealthState(backend, health, allowDegraded);
    if (healthStatus) {
      return { backend, healthStatus };
    }
  }

  const fallbackBackend = policy.defaultBackend ?? "local";
  const fallbackHealth = readHealthState(fallbackBackend, health, allowDegraded);
  if (fallbackHealth) {
    return { backend: fallbackBackend, healthStatus: fallbackHealth };
  }

  throw new Error("MODEL_ROUTING_CONTRACT_VIOLATION: no healthy backend available");
}

function buildSlot(taskClass: TaskClass, backend: BackendName, policy: RouteModelPolicy, memoryContext: RouteModelInput["memoryContext"]): string {
  if (isNonEmptyString(memoryContext.slot)) {
    return memoryContext.slot.trim();
  }
  const policySuffix = isNonEmptyString(policy.id) ? policy.id.trim() : "default";
  return `${taskClass}:${backend}:${policySuffix}`;
}

function buildAssistantContent(turn: NormalizedChatTurn, backend: BackendName, taskClass: TaskClass): string {
  return [
    `routed:${taskClass}`,
    `backend:${backend}`,
    `text:${turn.userText.trim()}`,
  ].join("\n");
}

export function routeModel(input: RouteModelInput): ValidatedAssistantPayload {
  if (!isPlainObject(input) || !isPlainObject(input.turn) || !isPlainObject(input.memoryContext)) {
    throw new Error("MODEL_ROUTING_CONTRACT_VIOLATION: normalized chat turn and memory context are required");
  }

  if (!isNonEmptyString(input.turn.userText)) {
    throw new Error("MODEL_ROUTING_CONTRACT_VIOLATION: turn.userText must be a non-empty string");
  }

  if (!Array.isArray(input.turn.history)) {
    throw new Error("MODEL_ROUTING_CONTRACT_VIOLATION: turn.history must be an array");
  }

  const history = input.turn.history.map((entry, index) => {
    if (!isPlainObject(entry)) {
      throw new Error(`MODEL_ROUTING_CONTRACT_VIOLATION: turn.history[${index}] must be a plain object`);
    }
    if (!isNonEmptyString(entry.content)) {
      throw new Error(`MODEL_ROUTING_CONTRACT_VIOLATION: turn.history[${index}].content must be a non-empty string`);
    }
    if (entry.role !== "system" && entry.role !== "user" && entry.role !== "assistant") {
      throw new Error(`MODEL_ROUTING_CONTRACT_VIOLATION: turn.history[${index}].role must be system, user, or assistant`);
    }
    return Object.freeze({
      role: entry.role,
      content: entry.content.trim(),
    }) as NormalizedChatTurn["history"][number];
  });

  const turn: NormalizedChatTurn = {
    requestId: assertNonEmptyOptionalString(input.turn.requestId, "turn.requestId"),
    sessionId: assertNonEmptyOptionalString(input.turn.sessionId, "turn.sessionId"),
    conversationId: assertNonEmptyOptionalString(input.turn.conversationId, "turn.conversationId"),
    userText: input.turn.userText.trim(),
    history: Object.freeze(history),
  };

  const memoryContext = input.memoryContext;
  if (memoryContext.taskClass !== undefined && normalizeTaskClass(memoryContext.taskClass) === null) {
    throw new Error("MODEL_ROUTING_CONTRACT_VIOLATION: memoryContext.taskClass is invalid");
  }
  if (memoryContext.slot !== undefined && !isNonEmptyString(memoryContext.slot)) {
    throw new Error("MODEL_ROUTING_CONTRACT_VIOLATION: memoryContext.slot must be a non-empty string");
  }
  if (memoryContext.modelPolicy !== undefined) {
    assertPlainObject(memoryContext.modelPolicy, "memoryContext.modelPolicy");
  }
  if (memoryContext.backendHealth !== undefined) {
    assertPlainObject(memoryContext.backendHealth, "memoryContext.backendHealth");
  }

  const taskClass = inferTaskClass(turn, memoryContext);
  const policy = readPolicy(memoryContext);
  const health = memoryContext.backendHealth as RouteModelHealth | undefined;
  const selected = selectBackend(taskClass, policy, health);
  const slot = buildSlot(taskClass, selected.backend, policy, memoryContext);

  return Object.freeze({
    role: "assistant",
    content: buildAssistantContent(turn, selected.backend, taskClass),
    model: `${selected.backend}:${taskClass}`,
    backend: selected.backend,
    slot,
    taskClass,
    validated: true,
    metadata: Object.freeze({
      policyId: isNonEmptyString(policy.id) ? policy.id.trim() : "default",
      healthStatus: selected.healthStatus,
      sessionId: turn.sessionId,
      conversationId: turn.conversationId,
      requestId: turn.requestId,
      historyDepth: turn.history.length,
    }),
  });
}
