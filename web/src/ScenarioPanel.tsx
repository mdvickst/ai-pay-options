import type { ReactNode } from "react";
import { Box, Button, Callout, CalloutHeading, CalloutText, Card, Heading, Separator, Stack, Text } from "@twilio-paste/core";
import type { DemoConfig, Scenario } from "./api";
import { NumberField } from "./fields";

export const SCENARIOS: { id: Scenario; label: string; summary: string; posture: string; variant: "success" | "warning" }[] = [
  {
    id: "pay_verb",
    label: "1 · <Pay> verb",
    summary: "The agent redirects the call to Twilio <Pay>. Twilio plays your prompts, collects keypad digits, and charges through the Generic Pay Connector, then the call returns to the agent.",
    posture: "Card data never reaches the LLM. Only the Pay connector endpoint sees it.",
    variant: "success",
  },
  {
    id: "payments_api",
    label: "2 · Agent-assisted Payments API",
    summary: "The AI agent stays on the call, moves through each capture step with the Payments API, and reacts to status webhooks for wrong-length input and silence.",
    posture: "Twilio captures the DTMF; the agent only sees masked status events.",
    variant: "success",
  },
  {
    id: "relay_pay",
    label: "3 · ConversationRelay pay socket",
    summary: "The call moves to a second ConversationRelay session whose WebSocket is a deterministic parser, not an LLM. Callers can speak or key their digits.",
    posture: "Spoken card data passes through STT and this server, so both are in PCI scope.",
    variant: "warning",
  },
  {
    id: "gather",
    label: "4 · <Gather> speech + DTMF",
    summary: "A <Gather> loop collects each field by speech or keypad, using class-token hints and server-side digit cleanup.",
    posture: "Card data reaches this webhook in clear text, so this server is in PCI scope.",
    variant: "warning",
  },
];

interface Props {
  cfg: DemoConfig;
  saved: boolean;
  onChange: (cfg: DemoConfig) => void;
  onSave: () => Promise<void>;
  onSelect: (scenario: Scenario) => void;
  renderForm: (cfg: DemoConfig, onChange: (cfg: DemoConfig) => void) => ReactNode;
}

/** Scenario switcher, scenario description, and the active scenario's config form. */
export function ScenarioPanel({ cfg, saved, onChange, onSave, onSelect, renderForm }: Props) {
  const active = SCENARIOS.find((s) => s.id === cfg.scenario)!;
  return (
    <Card padding="space80">
      <Heading as="h2" variant="heading30">
        Payment scenario
      </Heading>
      <Stack orientation="horizontal" spacing="space30">
        {SCENARIOS.map((s) => (
          <Button key={s.id} variant={s.id === cfg.scenario ? "primary" : "secondary"} size="small" onClick={() => onSelect(s.id)}>
            {s.label}
          </Button>
        ))}
      </Stack>
      <Box marginY="space60">
        <Text as="p" marginBottom="space40">
          {active.summary}
        </Text>
        <Callout variant={active.variant}>
          <CalloutHeading as="h3">PCI posture</CalloutHeading>
          <CalloutText>{active.posture}</CalloutText>
        </Callout>
      </Box>
      <Separator orientation="horizontal" verticalSpacing="space60" />
      {cfg.scenario !== "payments_api" && (
        <Box maxWidth="size40">
          <NumberField
            label="Max hand-off wait (seconds)"
            value={cfg.handoff_delay_seconds}
            onChange={(v) => onChange({ ...cfg, handoff_delay_seconds: v })}
            help="The call is redirected when ConversationRelay reports the hand-off line finished playing, or after this many seconds."
          />
        </Box>
      )}
      {renderForm(cfg, onChange)}
      <Box display="flex" alignItems="center" columnGap="space40" marginTop="space60">
        <Button variant="primary" onClick={onSave} disabled={saved}>
          Save settings
        </Button>
        <Text as="span" color="colorTextWeak">
          {saved ? "Saved" : "Unsaved changes, saved automatically when you call"}
        </Text>
      </Box>
    </Card>
  );
}
