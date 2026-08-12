/**
 * SQLite Schema v2 Implementation
 * 
 * Two-Tier Memory System:
 * - Tier 1: personal_facts (konkrete Fakten aus User-Input)
 * - Tier 2: patterns (abstrakte Anker mit Konfidenz)
 * - pattern_links: Verknüpfung Tier 1 ↔ Tier 2
 * 
 * Character System:
 * - attitudes: Dynamische Haltungen pro User (-10 bis +10)
 * - attitude_history: Zeitlicher Verlauf der Haltungen
 */

import type { Database } from "better-sqlite3";

export const SCHEMA_VERSION = 2;

export interface SchemaTables {
  // Tier 1: Personal Facts (konkrete Erinnerungen)
  personal_facts: {
    id: string;
    content: string;
    category: "preference" | "event" | "commitment" | "relationship";
    created_at: string;
    session_id: string;
    conversation_id: string;
    confidence: number; // 0.0 - 1.0
  };

  // Tier 2: Patterns (abstrakte Anker)
  patterns: {
    id: string;
    anchor: string;
    type: "preference" | "commitment" | "relationship" | "contradiction";
    confidence: number;
    examples_json: string; // JSON Array of example fact IDs
    created_at: string;
    last_reinforced: string;
    reinforcement_count: number;
  };

  // Verknüpfungen: Welche Fakten zu welchem Pattern gehören
  pattern_links: {
    pattern_id: string;
    fact_id: string;
    relation_type: "example" | "contradiction" | "reinforcement";
    created_at: string;
  };

  // Attitude Tracking pro User
  attitudes: {
    user_id: string;
    dimension: "warmth" | "respect" | "patience" | "trust";
    score: number; // -10 bis +10
    updated_at: string;
    history_json: string; // JSON Array of {timestamp, score, reason}
  };

  // Session Memory (bestehend aus v1)
  session_memory_entries: {
    id: string;
    session_id: string;
    conversation_id: string;
    role: "user" | "assistant" | "system";
    content: string;
    created_at: string;
    expires_at: string | null;
    metadata_json: string | null;
  };
}

/**
 * Migration von Schema v1 zu v2
 */
export function migrateToV2(db: Database): void {
  // Prüfe aktuelle Version
  const currentVersion = db.pragma("user_version") as number;
  
  if (currentVersion >= 2) {
    return; // Bereits v2 oder höher
  }

  db.transaction(() => {
    // Backup bestehende Daten
    db.exec(`
      ALTER TABLE session_memory_entries RENAME TO session_memory_entries_backup;
    `);

    // Neue Tabellen erstellen
    db.exec(createSchemaV2SQL);

    // Daten migrieren
    db.exec(`
      INSERT INTO session_memory_entries (
        id, session_id, conversation_id, role, content, 
        created_at, expires_at, metadata_json
      )
      SELECT 
        id, session_id, conversation_id, role, content,
        created_at, expires_at, 
        CASE 
          WHEN metadata IS NOT NULL THEN json_object('legacy', metadata)
          ELSE NULL 
        END as metadata_json
      FROM session_memory_entries_backup;
    `);

    // Alte Tabelle löschen
    db.exec(`DROP TABLE session_memory_entries_backup;`);

    // Version setzen
    db.pragma(`user_version = ${SCHEMA_VERSION}`);
  })();
}

/**
 * Komplettes Schema v2 SQL
 */
const createSchemaV2SQL = `
-- Session Memory (aus v1, mit metadata als JSON)
CREATE TABLE IF NOT EXISTS session_memory_entries (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT,
  metadata_json TEXT,
  
  INDEX idx_session_memory_session (session_id, conversation_id),
  INDEX idx_session_memory_created (created_at)
);

-- Tier 1: Personal Facts
CREATE TABLE IF NOT EXISTS personal_facts (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  category TEXT NOT NULL CHECK(category IN ('preference', 'event', 'commitment', 'relationship')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  session_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0 CHECK(confidence >= 0.0 AND confidence <= 1.0),
  
  INDEX idx_facts_session (session_id, conversation_id),
  INDEX idx_facts_category (category),
  INDEX idx_facts_created (created_at)
);

-- Tier 2: Patterns (Anker)
CREATE TABLE IF NOT EXISTS patterns (
  id TEXT PRIMARY KEY,
  anchor TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('preference', 'commitment', 'relationship', 'contradiction')),
  confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
  examples_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_reinforced TEXT NOT NULL DEFAULT (datetime('now')),
  reinforcement_count INTEGER NOT NULL DEFAULT 1,
  
  INDEX idx_patterns_type (type),
  INDEX idx_patterns_confidence (confidence),
  UNIQUE(anchor, type)
);

-- Pattern Links (Tier 1 ↔ Tier 2)
CREATE TABLE IF NOT EXISTS pattern_links (
  pattern_id TEXT NOT NULL,
  fact_id TEXT NOT NULL,
  relation_type TEXT NOT NULL CHECK(relation_type IN ('example', 'contradiction', 'reinforcement')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  
  PRIMARY KEY (pattern_id, fact_id),
  FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE,
  FOREIGN KEY (fact_id) REFERENCES personal_facts(id) ON DELETE CASCADE
);

-- Attitudes (Character Haltungen)
CREATE TABLE IF NOT EXISTS attitudes (
  user_id TEXT NOT NULL,
  dimension TEXT NOT NULL CHECK(dimension IN ('warmth', 'respect', 'patience', 'trust')),
  score INTEGER NOT NULL DEFAULT 0 CHECK(score >= -10 AND score <= 10),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  history_json TEXT NOT NULL DEFAULT '[]',
  
  PRIMARY KEY (user_id, dimension)
);

-- Pragma für Version
PRAGMA user_version = 2;
`;

/**
 * Initialisiere Schema v2 auf frischer Datenbank
 */
export function initializeSchemaV2(db: Database): void {
  db.exec(createSchemaV2SQL);
}
