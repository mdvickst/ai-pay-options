import { Box, Heading } from "@twilio-paste/core";
import type { PaymentsApiConfig } from "../api";
import { AreaField, BoolField, FieldGrid, NumberField, SelectField, TextField } from "../fields";

const FIELDS = ["payment-card-number", "expiration-date", "security-code", "postal-code"];

/** Scenario 2 form: Payments API session settings, retry limits, and the fixed keypad prompt per field. */
export function PaymentsApiForm({ cfg, onChange }: { cfg: PaymentsApiConfig; onChange: (c: PaymentsApiConfig) => void }) {
  const set = <K extends keyof PaymentsApiConfig>(k: K, v: PaymentsApiConfig[K]) => onChange({ ...cfg, [k]: v });
  return (
    <Box>
      <Heading as="h3" variant="heading40">
        Payment session
      </Heading>
      <FieldGrid>
        <TextField label="Payment connector" value={cfg.payment_connector} onChange={(v) => set("payment_connector", v)} help="Blank uses PAY_CONNECTOR from .env" />
        <SelectField label="Token type" value={cfg.token_type} options={["reusable", "one-time", "payment-method"]} onChange={(v) => set("token_type", v)} />
        <BoolField label="Charge the balance" value={cfg.charge} onChange={(v) => set("charge", v)} help="Off = tokenize only" />
        <TextField label="Valid card types" value={cfg.valid_card_types} onChange={(v) => set("valid_card_types", v)} />
        <BoolField label="Collect security code" value={cfg.security_code} onChange={(v) => set("security_code", v)} />
        <BoolField label="Collect postal code" value={cfg.postal_code} onChange={(v) => set("postal_code", v)} />
        <NumberField label="Digit timeout (seconds)" value={cfg.timeout} onChange={(v) => set("timeout", v)} />
        <BoolField label="Twilio confirmation step" value={cfg.confirmation} onChange={(v) => set("confirmation", v)} help="Caller hears last 4 and presses 1 to confirm" />
      </FieldGrid>
      <Heading as="h3" variant="heading40">
        No-input detection
      </Heading>
      <FieldGrid>
        <NumberField label="No-input seconds" value={cfg.no_input_seconds} onChange={(v) => set("no_input_seconds", v)} help="System repeats the prompt when no keys are pressed" />
        <NumberField label="Max no-input re-prompts" value={cfg.max_no_input_retries} onChange={(v) => set("max_no_input_retries", v)} help="Then the payment stops and the agent takes over" />
        <NumberField label="Max attempts per field" value={cfg.max_attempts} onChange={(v) => set("max_attempts", v)} help="Failed entries before the payment stops" />
      </FieldGrid>
      <Heading as="h3" variant="heading40">
        Keypad prompt per capture step
      </Heading>
      {FIELDS.map((f) => (
        <AreaField key={f} label={f} value={cfg.field_prompts[f] ?? ""} onChange={(v) => set("field_prompts", { ...cfg.field_prompts, [f]: v })} />
      ))}
    </Box>
  );
}
