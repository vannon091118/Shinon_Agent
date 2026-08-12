export type RuntimeEvent = Readonly<{
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
}>;

export type ErrorEnvelope = Readonly<{
  code: string;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}>;
