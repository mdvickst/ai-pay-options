import { useEffect, useState } from "react";
import { Badge, Box, Button, Card, Heading, Text } from "@twilio-paste/core";
import type { FeedEvent } from "./api";

const VARIANTS: Record<string, "neutral" | "info" | "success" | "warning" | "error" | "new"> = {
  call: "neutral",
  transcript: "info",
  agent: "new",
  tool: "warning",
  payment: "success",
  twiml: "neutral",
  error: "error",
};

/** Live timeline of server events from /api/events. */
export function EventFeed() {
  const [events, setEvents] = useState<FeedEvent[]>([]);

  useEffect(() => {
    const source = new EventSource("/api/events");
    source.onmessage = (m) => setEvents((prev) => [JSON.parse(m.data) as FeedEvent, ...prev].slice(0, 300));
    return () => source.close();
  }, []);

  return (
    <Card padding="space80">
      <Box display="flex" justifyContent="space-between" alignItems="center" marginBottom="space60">
        <Heading as="h2" variant="heading30" marginBottom="space0">
          Live events
        </Heading>
        <Button variant="secondary" size="small" onClick={() => setEvents([])}>
          Clear
        </Button>
      </Box>
      <Box maxHeight="70vh" overflowY="auto">
        {events.length === 0 && (
          <Text as="p" color="colorTextWeak">
            Waiting for a call…
          </Text>
        )}
        {events.map((e, i) => (
          <Box key={`${e.ts}-${i}`} paddingY="space40" borderBottomStyle="solid" borderBottomWidth="borderWidth10" borderBottomColor="colorBorderWeaker">
            <Box display="flex" columnGap="space30" alignItems="center">
              <Badge as="span" variant={VARIANTS[e.kind] ?? "neutral"}>
                {e.kind}
              </Badge>
              <Text as="span" fontSize="fontSize20" color="colorTextWeak">
                {new Date(e.ts * 1000).toLocaleTimeString()}
              </Text>
            </Box>
            <Text as="p" marginTop="space20">
              {e.title}
            </Text>
            {Object.keys(e.data).length > 0 && (
              <Box as="pre" fontFamily="fontFamilyCode" fontSize="fontSize20" whiteSpace="pre-wrap" backgroundColor="colorBackground" padding="space30" borderRadius="borderRadius20" marginTop="space20" marginBottom="space0">
                {JSON.stringify(e.data, null, 2)}
              </Box>
            )}
          </Box>
        ))}
      </Box>
    </Card>
  );
}
