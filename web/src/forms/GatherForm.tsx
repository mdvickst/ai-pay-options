import { Box, Heading } from "@twilio-paste/core";
import type { GatherField, GatherPayConfig } from "../api";
import { AreaField, BoolField, FieldGrid, NumberField, SelectField, TextField } from "../fields";

const FIELDS = ["card", "expiry", "cvv", "zip"];

/** Scenario 4 form: <Gather> speech settings plus prompt and class-token hints per field. */
export function GatherForm({ cfg, onChange }: { cfg: GatherPayConfig; onChange: (c: GatherPayConfig) => void }) {
  const set = <K extends keyof GatherPayConfig>(k: K, v: GatherPayConfig[K]) => onChange({ ...cfg, [k]: v });
  const setField = (f: string, patch: Partial<GatherField>) => set("fields", { ...cfg.fields, [f]: { ...cfg.fields[f], ...patch } });
  return (
    <Box>
      <Heading as="h3" variant="heading40">
        &lt;Gather&gt; settings
      </Heading>
      <FieldGrid>
        <SelectField label="Speech model" value={cfg.speech_model} options={["phone_call", "numbers_and_commands", "default", "experimental_utterances", "experimental_conversations"]} onChange={(v) => set("speech_model", v)} />
        <BoolField label="Enhanced (phone_call only)" value={cfg.enhanced} onChange={(v) => set("enhanced", v)} />
        <NumberField label="Timeout (seconds)" value={cfg.timeout} onChange={(v) => set("timeout", v)} />
        <TextField label="Speech timeout" value={cfg.speech_timeout} onChange={(v) => set("speech_timeout", v)} help='"auto" or seconds' />
        <TextField label="Finish on key" value={cfg.finish_on_key} onChange={(v) => set("finish_on_key", v)} />
        <NumberField label="Max attempts per field" value={cfg.max_attempts} onChange={(v) => set("max_attempts", v)} />
        <BoolField label="Show masked raw speech in feed" value={cfg.show_raw_speech} onChange={(v) => set("show_raw_speech", v)} />
      </FieldGrid>
      {FIELDS.map((f) => (
        <Box key={f}>
          <Heading as="h4" variant="heading50">
            {f}
          </Heading>
          <FieldGrid>
            <AreaField label="Prompt" value={cfg.fields[f].prompt} onChange={(v) => setField(f, { prompt: v })} />
            <TextField label="Hints" value={cfg.fields[f].hints} onChange={(v) => setField(f, { hints: v })} help="Class tokens, e.g. $OOV_CLASS_DIGIT_SEQUENCE $MONTH $YEAR $POSTALCODE" />
          </FieldGrid>
        </Box>
      ))}
    </Box>
  );
}
