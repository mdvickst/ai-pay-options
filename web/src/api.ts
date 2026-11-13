export type Scenario = "pay_verb" | "payments_api" | "relay_pay" | "gather";

export interface PayPrompt {
  field: string;
  error_type: string;
  attempt: string;
  card_type: string;
  require_matching_inputs: boolean;
  says: string[];
}

export interface PayVerbConfig {
  payment_connector: string;
  charge: boolean;
  currency: string;
  token_type: string;
  payment_method: string;
  bank_account_type: string;
  valid_card_types: string;
  max_attempts: number;
  timeout: number;
  postal_code: boolean;
  min_postal_code_length: number;
  security_code: boolean;
  language: string;
  description: string;
  prompts: PayPrompt[];
}

export interface PaymentsApiConfig {
  payment_connector: string;
  charge: boolean;
  token_type: string;
  valid_card_types: string;
  postal_code: boolean;
  security_code: boolean;
  timeout: number;
  confirmation: boolean;
  no_input_seconds: number;
  max_no_input_retries: number;
  max_attempts: number;
  field_prompts: Record<string, string>;
}

export interface RelayPayConfig {
  transcription_provider: string;
  speech_model: string;
  tts_provider: string;
  voice: string;
  hints: string;
  max_attempts: number;
  settle_seconds: number;
  no_input_seconds: number;
  prompts: Record<string, string>;
}

export interface GatherField {
  prompt: string;
  hints: string;
}

export interface GatherPayConfig {
  speech_model: string;
  enhanced: boolean;
  timeout: number;
  speech_timeout: string;
  finish_on_key: string;
  max_attempts: number;
  show_raw_speech: boolean;
  fields: Record<string, GatherField>;
}

export interface DemoConfig {
  scenario: Scenario;
  handoff_delay_seconds: number;
  pay_verb: PayVerbConfig;
  payments_api: PaymentsApiConfig;
  relay_pay: RelayPayConfig;
  gather: GatherPayConfig;
}

export interface FeedEvent {
  ts: number;
  kind: string;
  title: string;
  data: Record<string, unknown>;
  callSid: string | null;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

const send = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

/** Fetches the active demo config. */
export const getConfig = () => fetch("/api/config").then((r) => json<DemoConfig>(r));
/** Replaces the active demo config and returns the saved value. */
export const saveConfig = (cfg: DemoConfig) => fetch("/api/config", send("PUT", cfg)).then((r) => json<DemoConfig>(r));
/** Renders <Pay> TwiML for a scenario 1 config. */
export const previewPay = (cfg: PayVerbConfig) => fetch("/api/preview/pay", send("POST", cfg)).then((r) => json<{ twiml: string }>(r));
/** Fetches a Voice SDK access token. */
export const getToken = () => fetch("/api/token").then((r) => json<{ token: string; identity: string }>(r));
