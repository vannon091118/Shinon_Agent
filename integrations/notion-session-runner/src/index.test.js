import test from "node:test";
import assert from "node:assert/strict";
import { readProperty, UUID_RE } from "./index.js";

test("accepts a Notion page UUID", () => {
  assert.equal(UUID_RE.test("3f3eb55a-5817-813d-a128-e4682479196e"), true);
});

test("rejects a human-readable session key as a page UUID", () => {
  assert.equal(UUID_RE.test("SES-1"), false);
});

test("reads Notion title and rich text properties", () => {
  const page = {
    properties: {
      Session: { type: "title", title: [{ plain_text: "Pilot" }] },
      Ziel: { type: "rich_text", rich_text: [{ plain_text: "Validate preflight" }] },
    },
  };
  assert.equal(readProperty(page, "Session"), "Pilot");
  assert.equal(readProperty(page, "Ziel"), "Validate preflight");
});

test("reads select, status, url, and checkbox properties", () => {
  const page = {
    properties: {
      Phase: { type: "select", select: { name: "Preflight" } },
      Status: { type: "status", status: { name: "Bereit" } },
      Handoff: { type: "url", url: "https://example.invalid/handoff" },
      "Freigabe erforderlich": { type: "checkbox", checkbox: true },
    },
  };
  assert.equal(readProperty(page, "Phase"), "Preflight");
  assert.equal(readProperty(page, "Status"), "Bereit");
  assert.equal(readProperty(page, "Handoff"), "https://example.invalid/handoff");
  assert.equal(readProperty(page, "Freigabe erforderlich"), true);
});

test("missing properties return null", () => {
  assert.equal(readProperty({ properties: {} }, "Unknown"), null);
});