import { useState } from "react";
import { Box, Button, HelpText, Input, Option, Select, TBody, THead, Table, Td, TextArea, Th, Tr } from "@twilio-paste/core";
import type { PayPrompt } from "../api";
import { SelectField } from "../fields";
import { PRESETS } from "../presets";

const FOR_VALUES = ["payment-card-number", "expiration-date", "security-code", "postal-code", "bank-routing-number", "bank-account-number", "payment-processing"];
const EMPTY: PayPrompt = { field: "payment-card-number", error_type: "", attempt: "", card_type: "", require_matching_inputs: false, says: [""] };

/** Editable table of <Pay> <Prompt> rows with preset loading. */
export function PromptTable({ prompts, onChange }: { prompts: PayPrompt[]; onChange: (p: PayPrompt[]) => void }) {
  const [preset, setPreset] = useState("docs_credit_card");
  const update = (i: number, patch: Partial<PayPrompt>) => onChange(prompts.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  const labels = Object.fromEntries(Object.entries(PRESETS).map(([k, v]) => [k, v.label]));

  return (
    <Box>
      <Box display="flex" columnGap="space40" alignItems="flex-end">
        <Box flexGrow={1}>
          <SelectField label="Preset" value={preset} options={Object.keys(PRESETS)} labels={labels} onChange={setPreset} />
        </Box>
        <Box marginBottom="space50" display="flex" columnGap="space30">
          <Button variant="secondary" onClick={() => onChange(PRESETS[preset].prompts.map((p) => ({ ...p, says: [...p.says] })))}>
            Load preset
          </Button>
          <Button variant="secondary" onClick={() => onChange([...prompts, { ...EMPTY, says: [""] }])}>
            Add prompt
          </Button>
        </Box>
      </Box>
      <Table scrollHorizontally>
        <THead>
          <Tr>
            <Th>For</Th>
            <Th>Error type</Th>
            <Th>Attempt</Th>
            <Th>Card type</Th>
            <Th>Say (one per line)</Th>
            <Th />
          </Tr>
        </THead>
        <TBody>
          {prompts.map((p, i) => (
            <Tr key={i}>
              <Td>
                <Select aria-label="For" value={p.field} onChange={(e) => update(i, { field: e.target.value })}>
                  {FOR_VALUES.map((v) => (
                    <Option key={v} value={v}>
                      {v}
                    </Option>
                  ))}
                </Select>
              </Td>
              <Td>
                <Input aria-label="Error type" type="text" value={p.error_type} onChange={(e) => update(i, { error_type: e.target.value })} />
              </Td>
              <Td>
                <Input aria-label="Attempt" type="text" value={p.attempt} onChange={(e) => update(i, { attempt: e.target.value })} />
              </Td>
              <Td>
                <Input aria-label="Card type" type="text" value={p.card_type} onChange={(e) => update(i, { card_type: e.target.value })} />
              </Td>
              <Td>
                <TextArea aria-label="Say" value={p.says.join("\n")} onChange={(e) => update(i, { says: e.target.value.split("\n") })} />
              </Td>
              <Td>
                <Button variant="destructive_secondary" size="small" onClick={() => onChange(prompts.filter((_, j) => j !== i))}>
                  Remove
                </Button>
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
      <HelpText>
        errorType: timeout, invalid-card-number, invalid-card-type, invalid-date, invalid-security-code, invalid-postal-code, invalid-bank-routing-number, invalid-bank-account-number, input-matching-failed (space separated). Attempt: 1–10, e.g. "2 3". Card type: visa mastercard amex discover … (space separated).
      </HelpText>
    </Box>
  );
}
