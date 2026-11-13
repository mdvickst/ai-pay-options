import { Box, Callout, CalloutHeading, CalloutList, CalloutListItem, Heading } from "@twilio-paste/core";
import type { RelayPayConfig } from "../api";
import { AreaField, FieldGrid, NumberField, SelectField, TextField } from "../fields";

const PROMPTS = ["card", "expiry", "cvv", "zip", "confirm"];

/** Scenario 3 form: payment ConversationRelay STT/TTS, parser timing, prompts, and PCI notes. */
export function RelayPayForm({ cfg, onChange }: { cfg: RelayPayConfig; onChange: (c: RelayPayConfig) => void }) {
  const set = <K extends keyof RelayPayConfig>(k: K, v: RelayPayConfig[K]) => onChange({ ...cfg, [k]: v });
  return (
    <Box>
      <Box marginBottom="space60">
        <Callout variant="neutral">
          <CalloutHeading as="h3">Parsing spoken card numbers</CalloutHeading>
          <CalloutList as="ul">
            <CalloutListItem>Digits are parsed in this process with Microsoft Recognizers-Text plus Luhn, length, and expiry checks. No third-party NLU and no LLM sees them.</CalloutListItem>
            <CalloutListItem>No PCI-certified NLU for spoken card numbers was found. The STT provider must be PCI compliant per Twilio's Responsibility Matrix.</CalloutListItem>
            <CalloutListItem>Deepgram's redact=pci removes card numbers from transcripts. That protects logs but can't be used to capture the card.</CalloutListItem>
          </CalloutList>
        </Callout>
      </Box>
      <Heading as="h3" variant="heading40">
        ConversationRelay
      </Heading>
      <FieldGrid>
        <SelectField label="Transcription provider" value={cfg.transcription_provider} options={["Deepgram", "Google"]} onChange={(v) => set("transcription_provider", v)} />
        <TextField label="Speech model" value={cfg.speech_model} onChange={(v) => set("speech_model", v)} help="Deepgram: nova-3-general · Google: telephony" />
        <SelectField label="TTS provider" value={cfg.tts_provider} options={["", "ElevenLabs", "Google", "Amazon"]} onChange={(v) => set("tts_provider", v)} />
        <TextField label="Voice" value={cfg.voice} onChange={(v) => set("voice", v)} help="Blank uses the provider default" />
        <TextField label="Hints" value={cfg.hints} onChange={(v) => set("hints", v)} />
        <NumberField label="Max attempts per field" value={cfg.max_attempts} onChange={(v) => set("max_attempts", v)} />
        <NumberField label="Settle seconds" value={cfg.settle_seconds} onChange={(v) => set("settle_seconds", v)} help="Pause that ends a partially spoken field" />
        <NumberField label="No-input seconds" value={cfg.no_input_seconds} onChange={(v) => set("no_input_seconds", v)} />
      </FieldGrid>
      <Heading as="h3" variant="heading40">
        Prompts
      </Heading>
      {PROMPTS.map((k) => (
        <AreaField key={k} label={k} value={cfg.prompts[k] ?? ""} onChange={(v) => set("prompts", { ...cfg.prompts, [k]: v })} help={k === "confirm" ? "Placeholders: {brand} {last4} {amount}" : undefined} />
      ))}
    </Box>
  );
}
