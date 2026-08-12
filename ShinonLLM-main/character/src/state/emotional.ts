// PLACEHOLDER: character/state/emotional.ts
// Scope 0.3.0 - Aktuelle Stimmung pro Session
//
// TODO: Implementiere Session-basierte Emotional State:
//
// Während Attitudes langfristig sind (über Sessions), 
// ist der Emotional State kurzfristig (pro Session).
//
// Zustände:
// - neutral (Standard)
// - amused (User hat was Lustiges gesagt)
// - annoyed (User wiederholt sich / ignoriert Antworten)
// - concerned (User zeigt Problem-Muster)
// - curious (User bringt neues interessantes Thema)
//
// Reset: Jede neue Session startet mit "neutral"
// Ausnahme: Wenn Attitude.patience < 3 → startet mit "annoyed"

export type EmotionalState = 
  | "neutral"
  | "amused" 
  | "annoyed"
  | "concerned"
  | "curious"
  | "confrontational";  // Wenn Pattern erkannt wird

export type SessionEmotionalContext = {
  readonly sessionId: string;
  readonly currentState: EmotionalState;
  readonly previousStates: ReadonlyArray<{
    readonly state: EmotionalState;
    readonly triggeredBy: string;
    readonly timestamp: string;
  }>;
  readonly stateSince: string;  // ISO timestamp seit wann aktueller State aktiv
};

export function createEmotionalContext(sessionId: string): SessionEmotionalContext {
  return {
    sessionId,
    currentState: "neutral",
    previousStates: [],
    stateSince: new Date().toISOString(),
  };
}

export function transitionState(
  context: SessionEmotionalContext,
  newState: EmotionalState,
  reason: string
): SessionEmotionalContext {
  return {
    ...context,
    currentState: newState,
    previousStates: [
      ...context.previousStates,
      {
        state: context.currentState,
        triggeredBy: reason,
        timestamp: new Date().toISOString(),
      },
    ],
    stateSince: new Date().toISOString(),
  };
}

// PLACEHOLDER: State-influenced prompt modifiers
export function getToneModifier(state: EmotionalState): string {
  const modifiers: Record<EmotionalState, string> = {
    neutral: "behalte deinen normalen, trockenen Ton bei",
    amused: "zeige leichte Belustigung, aber bleib reserviert",
    annoyed: "sei direkter und kürzer, zeige leichte Irritation",
    concerned: "zeige vorsichtiges Interesse ohne zu kuschen",
    curious: "sei offener, aber behalte Skepsis bei",
    confrontational: "stelle die harte Frage direkt, keine Umschweife",
  };
  return modifiers[state];
}
