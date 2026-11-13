import { useEffect, useState } from "react";
import { Box, Spinner, Text } from "@twilio-paste/core";
import { Theme } from "@twilio-paste/core/theme";
import { getConfig, saveConfig, type DemoConfig, type Scenario } from "./api";
import { CallPanel } from "./CallPanel";
import { EventFeed } from "./EventFeed";
import { GatherForm } from "./forms/GatherForm";
import { PayVerbForm } from "./forms/PayVerbForm";
import { PaymentsApiForm } from "./forms/PaymentsApiForm";
import { RelayPayForm } from "./forms/RelayPayForm";
import { ScenarioPanel } from "./ScenarioPanel";

function renderForm(c: DemoConfig, on: (c: DemoConfig) => void) {
  switch (c.scenario) {
    case "pay_verb":
      return <PayVerbForm cfg={c.pay_verb} onChange={(v) => on({ ...c, pay_verb: v })} />;
    case "payments_api":
      return <PaymentsApiForm cfg={c.payments_api} onChange={(v) => on({ ...c, payments_api: v })} />;
    case "relay_pay":
      return <RelayPayForm cfg={c.relay_pay} onChange={(v) => on({ ...c, relay_pay: v })} />;
    case "gather":
      return <GatherForm cfg={c.gather} onChange={(v) => on({ ...c, gather: v })} />;
  }
}

/** Root page: top bar, scenario configuration, softphone, and live feed. */
export default function App() {
  const [cfg, setCfg] = useState<DemoConfig | null>(null);
  const [saved, setSaved] = useState(true);

  useEffect(() => {
    getConfig().then(setCfg);
  }, []);

  const change = (next: DemoConfig) => {
    setCfg(next);
    setSaved(false);
  };
  const save = async (next: DemoConfig | null = cfg) => {
    if (!next) return;
    setCfg(await saveConfig(next));
    setSaved(true);
  };
  const select = (scenario: Scenario) => {
    if (cfg) void save({ ...cfg, scenario });
  };

  return (
    <Theme.Provider theme="twilio">
      <Box backgroundColor="colorBackground" minHeight="100vh">
        <Box backgroundColor="colorBackgroundBrandStrong" paddingX="space80" paddingY="space60" display="flex" alignItems="center" columnGap="space40">
          <Text as="span" color="colorTextInverse" fontSize="fontSize50" fontWeight="fontWeightBold">
            ACME Inc.
          </Text>
          <Text as="span" color="colorTextInverseWeak" fontSize="fontSize40">
            Pay options on Twilio Programmable Voice
          </Text>
        </Box>
        {!cfg ? (
          <Box padding="space100">
            <Spinner decorative={false} title="Loading" size="sizeIcon70" />
          </Box>
        ) : (
          <Box padding="space80" display="grid" gridTemplateColumns="minmax(0, 3fr) minmax(360px, 2fr)" columnGap="space80" alignItems="start">
            <ScenarioPanel cfg={cfg} saved={saved} onChange={change} onSave={() => save()} onSelect={select} renderForm={renderForm} />
            <Box display="flex" flexDirection="column" rowGap="space80">
              <CallPanel beforeCall={() => (saved ? Promise.resolve() : save())} />
              <EventFeed />
            </Box>
          </Box>
        )}
      </Box>
    </Theme.Provider>
  );
}
