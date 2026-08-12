import { createHash } from "node:crypto";

function toHashInput(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (value instanceof Uint8Array) {
    return Buffer.from(value).toString("utf8");
  }

  if (value === undefined) {
    return "undefined";
  }

  const serialized = JSON.stringify(value);
  return serialized ?? String(value);
}

export function sha256Hex(value: unknown): string {
  return createHash("sha256").update(toHashInput(value)).digest("hex");
}

export function hash(value: unknown): string {
  return sha256Hex(value);
}
