// character/attitudes/tracker.ts - Scope 0.3.0
// Dynamische Haltungen pro User mit SQLite Persistenz

export type AttitudeDimension = "warmth" | "respect" | "patience" | "trust";

export type AttitudeState = {
  readonly userId: string;
  readonly warmth: number;   // -10 (kalt) to +10 (warm)
  readonly respect: number;  // -10 (verachtend) to +10 (wertschätzend)
  readonly patience: number; // -10 (genervt) to +10 (nachsichtig)
  readonly trust: number;    // -10 (misstrauisch) to +10 (vertrauend)
  readonly updatedAt: string;
  readonly history: ReadonlyArray<{
    readonly timestamp: string;
    readonly dimension: AttitudeDimension;
    readonly change: number;
    readonly reason: string;
  }>;
};

export type AttitudeSqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

export type AttitudeUpdateRule = {
  readonly event: string;
  readonly dimension: AttitudeDimension;
  readonly change: number;
};

// Standard-Update-Regeln für Attitude-Änderungen
export const ATTITUDE_UPDATE_RULES: ReadonlyArray<AttitudeUpdateRule> = [
  { event: "inkonsistenz_gefunden", dimension: "patience", change: -2 },
  { event: "inkonsistenz_gefunden", dimension: "respect", change: -1 },
  { event: "inkonsistenz_gefunden", dimension: "trust", change: -3 },
  { event: "versprechen_eingehalten", dimension: "trust", change: +3 },
  { event: "versprechen_eingehalten", dimension: "respect", change: +2 },
  { event: "versprechen_gebrochen", dimension: "trust", change: -5 },
  { event: "versprechen_gebrochen", dimension: "respect", change: -3 },
  { event: "positives_muster", dimension: "warmth", change: +1 },
  { event: "negatives_muster", dimension: "warmth", change: -1 },
  { event: "wiederholte_inkonsistenz", dimension: "patience", change: -3 },
  { event: "wiederholte_inkonsistenz", dimension: "trust", change: -4 },
];

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

/**
 * Lädt Attitude-State für einen User aus SQLite
 */
export function loadAttitudeState(
  adapter: AttitudeSqliteAdapter,
  userId: string
): AttitudeState {
  const rows = adapter.all(
    "SELECT dimension, score, updated_at FROM attitudes WHERE user_id = ?",
    [userId]
  );

  const baseState: AttitudeState = {
    userId,
    warmth: 0,
    respect: 0,
    patience: 5, // Start neutral-positive
    trust: 0,
    updatedAt: new Date().toISOString(),
    history: [],
  };

  for (const row of rows) {
    if (!isNonEmptyString(row.dimension)) continue;
    
    const dimension = row.dimension as AttitudeDimension;
    const score = typeof row.score === "number" ? row.score : 0;
    
    if (dimension === "warmth") {
      return { ...baseState, warmth: score };
    } else if (dimension === "respect") {
      return { ...baseState, respect: score };
    } else if (dimension === "patience") {
      return { ...baseState, patience: score };
    } else if (dimension === "trust") {
      return { ...baseState, trust: score };
    }
  }

  saveAttitudeState(adapter, baseState);
  return baseState;
}

/**
 * Speichert Attitude-State in SQLite
 */
export function saveAttitudeState(
  adapter: AttitudeSqliteAdapter,
  state: AttitudeState
): void {
  const now = new Date().toISOString();
  
  const dimensions: Array<{ key: AttitudeDimension; value: number }> = [
    { key: "warmth", value: state.warmth },
    { key: "respect", value: state.respect },
    { key: "patience", value: state.patience },
    { key: "trust", value: state.trust },
  ];

  for (const { key, value } of dimensions) {
    adapter.run(
      "INSERT OR REPLACE INTO attitudes (user_id, dimension, score, updated_at) VALUES (?, ?, ?, ?)",
      [state.userId, key, value, now]
    );
  }

  if (state.history.length > 0) {
    const recentHistory = state.history.slice(-10);
    adapter.run(
      "UPDATE attitudes SET history_json = ? WHERE user_id = ?",
      [JSON.stringify(recentHistory), state.userId]
    );
  }
}

/**
 * Erstellt initialen Attitude-State
 */
export function createAttitudeState(userId: string): AttitudeState {
  return {
    userId,
    warmth: 0,
    respect: 0,
    patience: 5,
    trust: 0,
    updatedAt: new Date().toISOString(),
    history: [],
  };
}

/**
 * Aktualisiert eine Attitude-Dimension
 */
export function updateAttitude(
  adapter: AttitudeSqliteAdapter,
  state: AttitudeState,
  dimension: AttitudeDimension,
  change: number,
  reason: string
): AttitudeState {
  const current = state[dimension];
  const next = Math.max(-10, Math.min(10, current + change));

  const newState: AttitudeState = {
    ...state,
    [dimension]: next,
    updatedAt: new Date().toISOString(),
    history: [
      ...state.history,
      {
        timestamp: new Date().toISOString(),
        dimension,
        change,
        reason,
      },
    ],
  };

  saveAttitudeState(adapter, newState);
  return newState;
}

/**
 * Wendet Attitude-Update-Regeln basierend auf Events an
 */
export function applyAttitudeRules(
  adapter: AttitudeSqliteAdapter,
  state: AttitudeState,
  event: string
): AttitudeState {
  const applicableRules = ATTITUDE_UPDATE_RULES.filter(r => r.event === event);
  
  let newState = state;
  for (const rule of applicableRules) {
    newState = updateAttitude(adapter, newState, rule.dimension, rule.change, event);
  }
  
  return newState;
}

/**
 * Prüft ob Konfrontations-Modus aktiviert werden soll
 */
export function shouldConfront(state: AttitudeState, patternConfidence: number): boolean {
  return state.patience < 5 && patternConfidence > 0.8;
}

/**
 * Formatiert Attitude-State für Prompt-Einbindung
 */
export function formatAttitudeForPrompt(state: AttitudeState): string {
  const format = (value: number, label: string) => {
    const bar = value >= 0 ? "█".repeat(Math.floor(value / 2)) + "░".repeat(5 - Math.floor(value / 2)) : "░".repeat(5);
    return `${label}: ${bar} (${value > 0 ? "+" : ""}${value}/10)`;
  };

  return [
    "Shinons aktuelle Haltung:",
    format(state.warmth, "Wärme"),
    format(state.respect, "Respekt"),
    format(state.patience, "Geduld"),
    format(state.trust, "Vertrauen"),
  ].join("\n");
}

/**
 * Holt Attitude-basierte Tondirektive für Prompts
 */
export function getToneDirective(state: AttitudeState): string {
  if (state.patience < 3) {
    return "Du bist genervt und direkt. Kurze, präzise Antworten ohne Umschweife.";
  }
  if (state.patience < 5) {
    return "Du bist sarkastisch und leicht gereizt.";
  }
  if (state.trust > 5) {
    return "Du bist warm und wertschätzend.";
  }
  if (state.trust < -5) {
    return "Du bist misstrauisch und distanziert.";
  }
  return "Du bist neutral und sachlich.";
}
