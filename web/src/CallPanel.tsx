import { useRef, useState } from "react";
import { Badge, Box, Button, Card, Heading, HelpText, Stack, Text } from "@twilio-paste/core";
import { Call, Device } from "@twilio/voice-sdk";
import { getToken } from "./api";
import { TextField } from "./fields";

type Status = "idle" | "connecting" | "in-call";
const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"];

/** Browser softphone that calls the ACME agent through the TwiML App. `beforeCall` runs first (saves config). */
export function CallPanel({ beforeCall }: { beforeCall: () => Promise<void> }) {
  const [callerNumber, setCallerNumber] = useState("+15555550100");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const device = useRef<Device | null>(null);
  const call = useRef<Call | null>(null);

  const start = async () => {
    setError("");
    setStatus("connecting");
    try {
      await beforeCall();
      if (!device.current) {
        const { token } = await getToken();
        device.current = new Device(token, { codecPreferences: [Call.Codec.Opus, Call.Codec.PCMU] });
      }
      const c = await device.current.connect({ params: { callerNumber } });
      call.current = c;
      c.on("accept", () => setStatus("in-call"));
      const reset = () => {
        call.current = null;
        setStatus("idle");
      };
      c.on("disconnect", reset);
      c.on("cancel", reset);
      c.on("error", (e: { message: string }) => {
        setError(e.message);
        reset();
      });
    } catch (e) {
      setError(String(e));
      setStatus("idle");
    }
  };

  return (
    <Card padding="space80">
      <Box display="flex" justifyContent="space-between" alignItems="center" marginBottom="space60">
        <Heading as="h2" variant="heading30" marginBottom="space0">
          Call ACME
        </Heading>
        <Badge as="span" variant={status === "in-call" ? "success" : status === "connecting" ? "warning" : "neutral"}>
          {status === "in-call" ? "On call" : status === "connecting" ? "Connecting" : "Idle"}
        </Badge>
      </Box>
      <TextField label="Caller number (used for balance lookup)" value={callerNumber} onChange={setCallerNumber} />
      <Stack orientation="horizontal" spacing="space40">
        {status === "idle" ? (
          <Button variant="primary" onClick={start}>
            Call the agent
          </Button>
        ) : (
          <Button variant="destructive" onClick={() => call.current?.disconnect()}>
            Hang up
          </Button>
        )}
      </Stack>
      {error && (
        <Box marginTop="space40">
          <HelpText variant="error">{error}</HelpText>
        </Box>
      )}
      <Box marginTop="space60">
        <Text as="p" fontWeight="fontWeightSemibold" marginBottom="space30">
          Keypad
        </Text>
        <Box display="grid" gridTemplateColumns="repeat(3, 1fr)" columnGap="space30" rowGap="space30" maxWidth="size30">
          {KEYS.map((k) => (
            <Button key={k} variant="secondary" fullWidth disabled={status !== "in-call"} onClick={() => call.current?.sendDigits(k)}>
              {k}
            </Button>
          ))}
        </Box>
      </Box>
    </Card>
  );
}
