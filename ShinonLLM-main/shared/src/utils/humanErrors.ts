export type HumanReadableError = {
  code: string;
  shortMessage: string;
  explanation: string;
  howToFix: string;
  context?: Record<string, unknown>;
};

function createError(
  code: string,
  shortMessage: string,
  explanation: string,
  howToFix: string,
  context?: Record<string, unknown>
): HumanReadableError {
  return {
    code,
    shortMessage,
    explanation,
    howToFix,
    context,
  };
}

export const ErrorCatalog = {
  // Memory Errors
  MEMORY_INVALID_INPUT: (field: string, value: unknown) =>
    createError(
      "MEMORY_INVALID_INPUT",
      `Ungültige Eingabe im Feld "${field}"`,
      `Das Feld "${field}" enthält einen Wert, den ich nicht verstehe: ${JSON.stringify(value)}.`,
      `Prüfe, dass "${field}" ein gültiger String, Objekt oder Array ist. Leere Werte oder falsche Typen führen zu diesem Fehler.`
    ),

  MEMORY_SESSION_NOT_FOUND: (sessionId: string) =>
    createError(
      "MEMORY_SESSION_NOT_FOUND",
      `Session "${sessionId.slice(0, 8)}..." nicht gefunden`,
      `Ich habe keine Daten für diese Session-ID im Gedächtnis. Entweder ist die Session zu alt und wurde archiviert, oder die ID ist falsch.`,
      `Stelle sicher, dass du die korrekte sessionId verwendest. Sessions älter als 10 Sitzungen landen im Cold Zone (Archiv) und sind nicht mehr direkt verfügbar.`
    ),

  MEMORY_TIER_VIOLATION: (tier: number, operation: string) =>
    createError(
      "MEMORY_TIER_VIOLATION",
      `Zugriffsverletzung auf Tier ${tier}`,
      `Du versuchst eine Operation auf Tier ${tier} auszuführen, die dort nicht erlaubt ist: ${operation}.`,
      `Tier 1 (Personal) enthält konkrete Fakten. Tier 2 (Pattern) enthält generalisierte Muster mit Links zu Tier 1. Prüfe, dass du die richtige Tier-Ebene für deine Operation verwendest.`
    ),

  MEMORY_ZONE_ACCESS_DENIED: (zone: string) =>
    createError(
      "MEMORY_ZONE_ACCESS_DENIED",
      `Zugriff auf ${zone} verweigert`,
      `Der Zugriff auf die ${zone} wurde abgelehnt. Das passiert, wenn du Daten aus einer Zone anfordern willst, für die du keine Berechtigung hast.`,
      `Hot Zone = aktuelle Session (offen). Mid Zone = letzte 10 Sessions (selektiv). Cold Zone = Archiv (nur via Pattern-Anker).`
    ),

  // Contract Errors
  CONTRACT_VALIDATION_FAILED: (field: string, expected: string, actual: unknown) =>
    createError(
      "CONTRACT_VALIDATION_FAILED",
      `Validierung fehlgeschlagen: ${field}`,
      `Das Feld "${field}" hat nicht den erwarteten Wert. Erwartet: ${expected}, erhalten: ${JSON.stringify(actual)}.`,
      `Prüfe deine Eingabedaten gegen den Contract. Alle Felder müssen den definierten Typen und Formaten entsprechen. Siehe LLM_ENTRY.md für die Pflicht-Lesereihenfolge.`
    ),

  CONTRACT_MISSING_FIELD: (field: string) =>
    createError(
      "CONTRACT_MISSING_FIELD",
      `Pflichtfeld fehlt: ${field}`,
      `Das Feld "${field}" ist erforderlich, aber nicht vorhanden.`,
      `Füge das Feld "${field}" zu deiner Anfrage hinzu. Siehe docs/HANDSHAKE_CURRENT_STATE.md für aktuelle Requirements.`
    ),

  // Backend Errors
  BACKEND_CONNECTION_FAILED: (backend: string, url: string) =>
    createError(
      "BACKEND_CONNECTION_FAILED",
      `Verbindung zu ${backend} fehlgeschlagen`,
      `Ich konnte keine Verbindung zum ${backend} Backend herstellen (URL: ${url}).`,
      `1. Prüfe, ob ${backend} läuft (docker ps / tasklist). 2. Prüfe die URL in den Umgebungsvariabellen (OLLAMA_BASE_URL / LLAMA_CPP_BASE_URL). 3. Für llama.setup siehe docs/LOCAL_LLAMACPP_SETUP.md`
    ),

  BACKEND_TIMEOUT: (backend: string, timeoutMs: number) =>
    createError(
      "BACKEND_TIMEOUT",
      `${backend} hat nicht rechtzeitig geantwortet`,
      `Das ${backend} Backend hat innerhalb von ${timeoutMs}ms keine Antwort geliefert.`,
      `1. Für große Modelle (>3B) erhöhe die timeoutMs im RouteDecision. 2. Prüfe die Systemlast (CPU/RAM). 3. Reduziere maxTokens für schnellere Antworten.`
    ),

  BACKEND_INVALID_RESPONSE: (backend: string, reason: string) =>
    createError(
      "BACKEND_INVALID_RESPONSE",
      `Ungültige Antwort von ${backend}`,
      `${backend} hat eine Antwort geliefert, die ich nicht verstehe: ${reason}.`,
      `Prüfe die Modell-Konfiguration. Einige Modelle liefern unerwartete Formate. Siehe docs/LOCAL_LLAMACPP_SETUP.md für getestete Modelle.`
    ),

  // Schema/Determinism Errors
  SCHEMA_VERSION_MISMATCH: (expected: number, actual: number) =>
    createError(
      "SCHEMA_VERSION_MISMATCH",
      `Schema-Version ${actual} nicht unterstützt`,
      `Die Datenbank läuft mit Schema v${actual}, aber ich unterstütze nur bis v${expected}.`,
      `Führe eine Migration durch (siehe MEMORY_POLICY.md "v1 → v2 Migration") oder setze eine neue Datenbank auf mit SHINON_MEMORY_SQLITE_PATH.`
    ),

  REPLAY_HASH_MISMATCH: (expected: string, actual: string) =>
    createError(
      "REPLAY_HASH_MISMATCH",
      "Determinismus verletzt",
      `Der Replay-Hash stimmt nicht überein. Erwartet: ${expected.slice(0, 16)}..., erhalten: ${actual.slice(0, 16)}....`,
      `Dies deutet auf nicht-deterministisches Verhalten hin. 1. Prüfe Zeitstempel/Zufallswerte im Code. 2. Stelle sicher, dass alle Sortierungen stabil sind. 3. Siehe tests/gates/replay-gate.spec.ts`
    ),

  // Pattern/Character Errors
  PATTERN_EXTRACTION_FAILED: (input: string, reason: string) =>
    createError(
      "PATTERN_EXTRACTION_FAILED",
      "Pattern-Erkennung fehlgeschlagen",
      `Ich konnte kein Muster aus dem Input erkennen: "${input.slice(0, 50)}...". Grund: ${reason}.`,
      `Pattern-Erkennung funktioniert nur für bestimmte Kategorien (preference, commitment, relationship, contradiction). Für andere Inhalte gibt es keine Pattern.`
    ),

  ATTITUDE_OUT_OF_RANGE: (dimension: string, value: number) =>
    createError(
      "ATTITUDE_OUT_OF_RANGE",
      `Ungültiger Attitude-Wert: ${value}`,
      `Der Attitude-Wert für "${dimension}" muss zwischen -10 und +10 liegen, aber ${value} wurde angegeben.`,
      `Normalisiere den Wert auf den Bereich [-10, 10] bevor du ihn speicherst.`
    ),

  // Generic
  UNKNOWN_ERROR: (context?: string) =>
    createError(
      "UNKNOWN_ERROR",
      "Ein unerwarteter Fehler ist aufgetreten",
      context || "Irgendetwas ist schiefgelaufen, aber ich weiß nicht genau was.",
      `Prüfe die Logs mit mehr Details. Wenn das Problem bestehen bleibt, siehe docs/OPS_PLAYBOOKS.md für Troubleshooting-Steps.`
    ),
} as const;

export function failClosedWithHumanMessage(
  errorKey: keyof typeof ErrorCatalog,
  ...args: unknown[]
): never {
  const errorFn = ErrorCatalog[errorKey] as (...args: unknown[]) => HumanReadableError;
  const error = errorFn(...args);
  
  throw {
    ...error,
    toString() {
      return `[${this.code}] ${this.shortMessage}\n\n${this.explanation}\n\nSo behebst du es:\n${this.howToFix}`;
    },
  };
}

// Legacy failClosed für Abwärtskompatibilität
export function failClosed(code: string, message: string, context?: Record<string, unknown>): never {
  throw {
    code,
    shortMessage: message,
    explanation: message,
    howToFix: "Siehe Fehlercode-Dokumentation für Details.",
    context,
    toString() {
      return `[${this.code}] ${this.shortMessage}`;
    },
  };
}
