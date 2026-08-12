// PLACEHOLDER: character/prompts/generator.ts
// Scope 0.3.0 - "Shinons Gedanken"-Prompts für LLM
//
// TODO: Implementiere Prompt Generator:
//
// Statt statischer System-Prompts generiert die Runtime
// nach jedem Input einen "Gedanken-Prompt" für das LLM.
//
// Input:
// - userText: Was der User gesagt hat
// - patterns: Relevante Patterns aus Tier 2
// - attitude: Aktuelle Haltungs-Werte
// - emotionalState: Aktuelle Stimmung
// - relevantFacts: Verknüpfte Fakten aus Tier 1
//
// Output:
// - Prompt im Format: "Ich (Shinon) denke..."
// - Enthält: Patterns, Attitudes, Facts, Tone
// - LLM generiert Antwort basierend auf diesem Kontext

import type { AttitudeState } from "../attitudes/tracker.js";
import type { EmotionalState } from "../state/emotional.js";
import type { Pattern } from "../experience/patterns.js";

export type PromptContext = {
  readonly userText: string;
  readonly patterns: ReadonlyArray<Pattern>;
  readonly attitude: AttitudeState;
  readonly emotionalState: EmotionalState;
  readonly relevantFacts: ReadonlyArray<{
    readonly id: string;
    readonly content: string;
    readonly date: string;
  }>;
  readonly interactionCount: number;
};

export type GeneratedPrompt = {
  readonly systemPrompt: string;
  readonly userPrompt: string;
  readonly toneDirective: string;
  readonly referencedPatterns: ReadonlyArray<string>;
  readonly referencedFacts: ReadonlyArray<string>;
};

// PLACEHOLDER: Prompt Template
const SHINON_PROMPT_TEMPLATE = `Du bist Shinon. Du hast mit diesem User {{interactionCount}} Interaktionen.

Deine aktuelle Haltung:
- Wärme: {{attitude.warmth}}/10 ({{warmthDescription}})
- Respekt: {{attitude.respect}}/10 ({{respectDescription}})
- Geduld: {{attitude.patience}}/10 ({{patienceDescription}})
- Vertrauen: {{attitude.trust}}/10 ({{trustDescription}})

Erkannte Muster:
{{patterns}}

Relevante Erinnerungen:
{{facts}}

Deine aktuelle Stimmung: {{emotionalState}}
{{toneDirective}}

User Input: {{userText}}

Antworte als Shinon. Dein Ton sollte deine Haltung widerspiegeln.
Wenn Geduld < 4, sei direkter/sarkastischer.
Wenn ein Muster mit Konfidenz > 0.8 erkannt wurde, adressiere es explizit.`;

export function generatePrompt(context: PromptContext): GeneratedPrompt {
  // TODO: Implementiere Template-Rendering mit Kontext-Daten
  // TODO: Formatiere Patterns und Facts menschenleslich
  // TODO: Generiere toneDirective basierend auf attitude + emotionalState
  
  return {
    systemPrompt: SHINON_PROMPT_TEMPLATE,  // Placeholder
    userPrompt: context.userText,
    toneDirective: "behalte trockenen Ton bei",
    referencedPatterns: context.patterns.map(p => p.anchor),
    referencedFacts: context.relevantFacts.map(f => f.id),
  };
}

// PLACEHOLDER: Confrontation Prompt
export function generateConfrontationPrompt(
  pattern: Pattern,
  contradiction: { older: { date: string; content: string }; newer: { date: string; content: string } }
): string {
  return `Ich muss dich auf etwas ansprechen. Am ${contradiction.older.date} hast du gesagt: "${contradiction.older.content}". Jetzt sagst du: "${contradiction.newer.content}". Was ist da los?`;
}
