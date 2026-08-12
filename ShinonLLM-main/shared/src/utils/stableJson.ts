export function stableStringify(value: unknown): string {
  const seen = new WeakSet<object>();

  function normalize(input: unknown): unknown {
    if (input === null || typeof input !== "object") {
      return input;
    }

    if (Array.isArray(input)) {
      return input.map(normalize);
    }

    if (seen.has(input)) {
      return "[Circular]";
    }

    seen.add(input);
    const output: Record<string, unknown> = {};
    for (const key of Object.keys(input).sort()) {
      output[key] = normalize((input as Record<string, unknown>)[key]);
    }
    return output;
  }

  return JSON.stringify(normalize(value));
}

export const stableJson = stableStringify;
