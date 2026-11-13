import { useEffect, useState } from "react";
import { Box, Heading } from "@twilio-paste/core";
import { previewPay, type PayVerbConfig } from "../api";
import { BoolField, FieldGrid, NumberField, SelectField, TextField } from "../fields";
import { PromptTable } from "./PromptTable";

/** Scenario 1 form: <Pay> attributes, prompt editor, and live TwiML preview. */
export function PayVerbForm({ cfg, onChange }: { cfg: PayVerbConfig; onChange: (c: PayVerbConfig) => void }) {
  const set = <K extends keyof PayVerbConfig>(k: K, v: PayVerbConfig[K]) => onChange({ ...cfg, [k]: v });
  const [twiml, setTwiml] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      previewPay(cfg)
        .then((r) => setTwiml(r.twiml.replace(/></g, ">\n<")))
        .catch((e) => setTwiml(String(e)));
    }, 300);
    return () => clearTimeout(t);
  }, [cfg]);

  return (
    <Box>
      <Heading as="h3" variant="heading40">
        &lt;Pay&gt; attributes
      </Heading>
      <FieldGrid>
        <TextField label="Payment connector" value={cfg.payment_connector} onChange={(v) => set("payment_connector", v)} help="Blank uses PAY_CONNECTOR from .env" />
        <SelectField label="Payment method" value={cfg.payment_method} options={["credit-card", "ach-debit"]} onChange={(v) => set("payment_method", v)} />
        <BoolField label="Charge the balance" value={cfg.charge} onChange={(v) => set("charge", v)} help="Off = tokenize only (no chargeAmount)" />
        <SelectField label="Token type" value={cfg.token_type} options={["reusable", "one-time", "payment-method"]} onChange={(v) => set("token_type", v)} />
        <TextField label="Valid card types" value={cfg.valid_card_types} onChange={(v) => set("valid_card_types", v)} />
        <TextField label="Currency" value={cfg.currency} onChange={(v) => set("currency", v)} />
        <NumberField label="Max attempts" value={cfg.max_attempts} onChange={(v) => set("max_attempts", v)} help="Retries per field, 1–3" />
        <NumberField label="Timeout (seconds)" value={cfg.timeout} onChange={(v) => set("timeout", v)} help="Wait between digits" />
        <BoolField label="Collect security code" value={cfg.security_code} onChange={(v) => set("security_code", v)} />
        <BoolField label="Collect postal code" value={cfg.postal_code} onChange={(v) => set("postal_code", v)} />
        <NumberField label="Min postal code length" value={cfg.min_postal_code_length} onChange={(v) => set("min_postal_code_length", v)} />
        <TextField label="Language" value={cfg.language} onChange={(v) => set("language", v)} />
        <SelectField label="Bank account type (ACH)" value={cfg.bank_account_type} options={["consumer-checking", "consumer-savings", "commercial-checking"]} onChange={(v) => set("bank_account_type", v)} />
        <TextField label="Description" value={cfg.description} onChange={(v) => set("description", v)} />
      </FieldGrid>
      <Heading as="h3" variant="heading40">
        Prompts
      </Heading>
      <PromptTable prompts={cfg.prompts} onChange={(p) => set("prompts", p)} />
      <Box marginTop="space60">
        <Heading as="h3" variant="heading40">
          Generated TwiML
        </Heading>
        <Box as="pre" fontFamily="fontFamilyCode" fontSize="fontSize20" whiteSpace="pre-wrap" backgroundColor="colorBackgroundStrong" padding="space50" borderRadius="borderRadius30" maxHeight="size50" overflowY="auto">
          {twiml}
        </Box>
      </Box>
    </Box>
  );
}
