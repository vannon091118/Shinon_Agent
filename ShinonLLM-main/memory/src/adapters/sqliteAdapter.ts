/**
 * SQLite Database Adapter - Echte Implementierung (keine Stubs)
 * 
 * Verwaltet die Verbindung zu SQLite und führt tatsächliche CRUD-Operationen durch.
 * Pfad: %LOCALAPPDATA%/ShinonLLM/session-memory.sqlite
 */

import Database from "better-sqlite3";
import { join } from "node:path";
import { homedir } from "node:os";
import { mkdirSync } from "node:fs";
import { initializeSchemaV2, migrateToV2 } from "../schema/v2.js";

// Singleton-Instanz
let dbInstance: Database | null = null;

/**
 * Datenbank-Pfad ermitteln
 */
function getDatabasePath(): string {
  const appData = process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local");
  const dbDir = join(appData, "ShinonLLM");
  
  // Verzeichnis erstellen falls nicht existiert
  try {
    mkdirSync(dbDir, { recursive: true });
  } catch {
    // Ignoriere Fehler (existiert bereits)
  }
  
  return join(dbDir, "session-memory.sqlite");
}

/**
 * Datenbank-Verbindung herstellen (Singleton)
 */
export function getDatabase(): Database {
  if (dbInstance) {
    return dbInstance;
  }
  
  const dbPath = getDatabasePath();
  console.log(`[SQLite] Connecting to ${dbPath}`);
  
  dbInstance = new Database(dbPath);
  
  // Performance-Optimierungen
  dbInstance.pragma("journal_mode = WAL");
  dbInstance.pragma("foreign_keys = ON");
  dbInstance.pragma("synchronous = NORMAL");
  
  // Schema initialisieren/migrieren
  const currentVersion = dbInstance.pragma("user_version") as number;
  console.log(`[SQLite] Current schema version: ${currentVersion}`);
  
  if (currentVersion === 0) {
    console.log("[SQLite] Initializing schema v2...");
    initializeSchemaV2(dbInstance);
  } else if (currentVersion < 2) {
    console.log("[SQLite] Migrating to schema v2...");
    migrateToV2(dbInstance);
  }
  
  return dbInstance;
}

/**
 * Datenbank-Verbindung schliessen
 */
export function closeDatabase(): void {
  if (dbInstance) {
    console.log("[SQLite] Closing database connection");
    dbInstance.close();
    dbInstance = null;
  }
}

// ============================================================================
// TIER 1: Personal Facts CRUD
// ============================================================================

export interface PersonalFactRow {
  id: string;
  content: string;
  category: "preference" | "event" | "commitment" | "relationship";
  created_at: string;
  session_id: string;
  conversation_id: string;
  confidence: number;
}

/**
 * Neuen Fakt in Tier 1 speichern
 */
export function insertFact(fact: Omit<PersonalFactRow, "id"> & { id?: string }): string {
  const db = getDatabase();
  const id = fact.id || `fact_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  const stmt = db.prepare(`
    INSERT INTO personal_facts (id, content, category, session_id, conversation_id, confidence)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  
  stmt.run(
    id,
    fact.content,
    fact.category,
    fact.session_id,
    fact.conversation_id,
    fact.confidence ?? 1.0
  );
  
  console.log(`[SQLite] Inserted fact: ${id} (${fact.category})`);
  return id;
}

/**
 * Fakten aus Tier 1 abfragen
 */
export function queryFacts(options: {
  sessionId?: string;
  category?: string;
  limit?: number;
  since?: string;
}): PersonalFactRow[] {
  const db = getDatabase();
  
  let sql = "SELECT * FROM personal_facts WHERE 1=1";
  const params: (string | number)[] = [];
  
  if (options.sessionId) {
    sql += " AND session_id = ?";
    params.push(options.sessionId);
  }
  
  if (options.category) {
    sql += " AND category = ?";
    params.push(options.category);
  }
  
  if (options.since) {
    sql += " AND created_at >= ?";
    params.push(options.since);
  }
  
  sql += " ORDER BY created_at DESC";
  
  if (options.limit) {
    sql += " LIMIT ?";
    params.push(options.limit);
  }
  
  const stmt = db.prepare(sql);
  return stmt.all(...params) as PersonalFactRow[];
}

/**
 * Alle Fakten für eine Session abrufen (Hot Zone)
 */
export function getSessionFacts(sessionId: string): PersonalFactRow[] {
  return queryFacts({ sessionId, limit: 100 });
}

// ============================================================================
// TIER 2: Patterns CRUD
// ============================================================================

export interface PatternRow {
  id: string;
  anchor: string;
  type: "preference" | "commitment" | "relationship" | "contradiction";
  confidence: number;
  examples_json: string;
  created_at: string;
  last_reinforced: string;
  reinforcement_count: number;
}

/**
 * Neuen Pattern-Anker erstellen oder bestehenden verstaerken
 */
export function upsertPattern(pattern: {
  anchor: string;
  type: PatternRow["type"];
  exampleFactId: string;
  confidence?: number;
}): string {
  const db = getDatabase();
  const id = `pattern_${pattern.type}_${pattern.anchor.replace(/[^a-z0-9]/g, "_")}`;
  
  // Prüfe ob Pattern existiert
  const existing = db.prepare("SELECT * FROM patterns WHERE id = ?").get(id) as PatternRow | undefined;
  
  if (existing) {
    // Verstaerken: Beispiel hinzufuegen, Konfidenz updaten
    const examples = JSON.parse(existing.examples_json);
    if (!examples.includes(pattern.exampleFactId)) {
      examples.push(pattern.exampleFactId);
    }
    
    const stmt = db.prepare(`
      UPDATE patterns 
      SET reinforcement_count = reinforcement_count + 1,
          last_reinforced = datetime('now'),
          examples_json = ?,
          confidence = MAX(confidence, ?)
      WHERE id = ?
    `);
    
    stmt.run(JSON.stringify(examples), pattern.confidence ?? 0.7, id);
    console.log(`[SQLite] Reinforced pattern: ${id} (count: ${existing.reinforcement_count + 1})`);
  } else {
    // Neu erstellen
    const stmt = db.prepare(`
      INSERT INTO patterns (id, anchor, type, confidence, examples_json, reinforcement_count)
      VALUES (?, ?, ?, ?, ?, 1)
    `);
    
    stmt.run(
      id,
      pattern.anchor,
      pattern.type,
      pattern.confidence ?? 0.7,
      JSON.stringify([pattern.exampleFactId])
    );
    console.log(`[SQLite] Created pattern: ${id}`);
  }
  
  return id;
}

/**
 * Patterns abfragen (Tier 2)
 */
export function queryPatterns(options: {
  type?: string;
  minConfidence?: number;
  limit?: number;
}): PatternRow[] {
  const db = getDatabase();
  
  let sql = "SELECT * FROM patterns WHERE 1=1";
  const params: (string | number)[] = [];
  
  if (options.type) {
    sql += " AND type = ?";
    params.push(options.type);
  }
  
  if (options.minConfidence !== undefined) {
    sql += " AND confidence >= ?";
    params.push(options.minConfidence);
  }
  
  sql += " ORDER BY confidence DESC, last_reinforced DESC";
  
  if (options.limit) {
    sql += " LIMIT ?";
    params.push(options.limit);
  }
  
  const stmt = db.prepare(sql);
  return stmt.all(...params) as PatternRow[];
}

/**
 * Pattern mit Fakten verknuepfen
 */
export function linkPatternToFact(
  patternId: string,
  factId: string,
  relationType: "example" | "contradiction" | "reinforcement" = "example"
): void {
  const db = getDatabase();
  
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO pattern_links (pattern_id, fact_id, relation_type)
    VALUES (?, ?, ?)
  `);
  
  stmt.run(patternId, factId, relationType);
}

// ============================================================================
// Attitudes CRUD
// ============================================================================

export interface AttitudeRow {
  user_id: string;
  dimension: "warmth" | "respect" | "patience" | "trust";
  score: number;
  updated_at: string;
  history_json: string;
}

/**
 * Attitude-Wert updaten (mit History)
 */
export function updateAttitude(
  userId: string,
  dimension: AttitudeRow["dimension"],
  delta: number,
  reason: string
): number {
  const db = getDatabase();
  
  // Aktuellen Wert laden
  const existing = db.prepare("SELECT * FROM attitudes WHERE user_id = ? AND dimension = ?")
    .get(userId, dimension) as AttitudeRow | undefined;
  
  let newScore: number;
  let history: Array<{ timestamp: string; score: number; reason: string }>;
  
  if (existing) {
    newScore = Math.max(-10, Math.min(10, existing.score + delta));
    history = JSON.parse(existing.history_json);
  } else {
    newScore = Math.max(-10, Math.min(10, delta));
    history = [];
  }
  
  // History erweitern
  history.push({
    timestamp: new Date().toISOString(),
    score: newScore,
    reason
  });
  
  // Auf letzte 50 Eintraege beschraenken
  if (history.length > 50) {
    history = history.slice(-50);
  }
  
  // Upsert
  const stmt = db.prepare(`
    INSERT INTO attitudes (user_id, dimension, score, history_json)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id, dimension) DO UPDATE SET
      score = excluded.score,
      updated_at = datetime('now'),
      history_json = excluded.history_json
  `);
  
  stmt.run(userId, dimension, newScore, JSON.stringify(history));
  console.log(`[SQLite] Updated attitude: ${userId}.${dimension} = ${newScore} (${reason})`);
  
  return newScore;
}

/**
 * Alle Attitudes fuer einen User laden
 */
export function getUserAttitudes(userId: string): Record<string, number> {
  const db = getDatabase();
  
  const rows = db.prepare("SELECT * FROM attitudes WHERE user_id = ?")
    .all(userId) as AttitudeRow[];
  
  const result: Record<string, number> = {
    warmth: 0,
    respect: 0,
    patience: 5, // Default: etwas geduldig
    trust: 0
  };
  
  for (const row of rows) {
    result[row.dimension] = row.score;
  }
  
  return result;
}

// ============================================================================
// Session Memory (bestehend aus v1)
// ============================================================================

export interface SessionMemoryEntry {
  id: string;
  session_id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

/**
 * Session-Memory Eintrag speichern
 */
export function insertSessionMemory(entry: Omit<SessionMemoryEntry, "id">): string {
  const db = getDatabase();
  const id = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  const stmt = db.prepare(`
    INSERT INTO session_memory_entries (id, session_id, conversation_id, role, content)
    VALUES (?, ?, ?, ?, ?)
  `);
  
  stmt.run(id, entry.session_id, entry.conversation_id, entry.role, entry.content);
  return id;
}

/**
 * Session-Verlauf laden
 */
export function getSessionHistory(
  sessionId: string,
  conversationId?: string,
  limit = 100
): SessionMemoryEntry[] {
  const db = getDatabase();
  
  let sql = "SELECT * FROM session_memory_entries WHERE session_id = ?";
  const params: (string | number)[] = [sessionId];
  
  if (conversationId) {
    sql += " AND conversation_id = ?";
    params.push(conversationId);
  }
  
  sql += " ORDER BY created_at ASC LIMIT ?";
  params.push(limit);
  
  const stmt = db.prepare(sql);
  return stmt.all(...params) as SessionMemoryEntry[];
}
