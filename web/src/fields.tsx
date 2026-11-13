import { useId, type ReactNode } from "react";
import { Box, HelpText, Input, Label, Option, Select, Switch, TextArea } from "@twilio-paste/core";

interface Base<T> {
  label: string;
  value: T;
  onChange: (v: T) => void;
  help?: string;
}

/** Two-column grid for form fields. */
export function FieldGrid({ children }: { children: ReactNode }) {
  return (
    <Box display="grid" gridTemplateColumns="1fr 1fr" columnGap="space60">
      {children}
    </Box>
  );
}

/** Labeled single-line text input. */
export function TextField({ label, value, onChange, help }: Base<string>) {
  const id = useId();
  return (
    <Box marginBottom="space50">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type="text" value={value} onChange={(e) => onChange(e.target.value)} />
      {help && <HelpText>{help}</HelpText>}
    </Box>
  );
}

/** Labeled numeric input. */
export function NumberField({ label, value, onChange, help }: Base<number>) {
  const id = useId();
  return (
    <Box marginBottom="space50">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type="number" value={String(value)} onChange={(e) => onChange(Number(e.target.value))} />
      {help && <HelpText>{help}</HelpText>}
    </Box>
  );
}

/** Labeled on/off switch. */
export function BoolField({ label, value, onChange, help }: Base<boolean>) {
  return (
    <Box marginBottom="space50">
      <Switch checked={value} onChange={(e) => onChange(e.target.checked)} helpText={help}>
        {label}
      </Switch>
    </Box>
  );
}

/** Labeled select over string options. */
export function SelectField({ label, value, onChange, help, options, labels }: Base<string> & { options: string[]; labels?: Record<string, string> }) {
  const id = useId();
  return (
    <Box marginBottom="space50">
      <Label htmlFor={id}>{label}</Label>
      <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <Option key={o} value={o}>
            {labels?.[o] ?? (o || "(default)")}
          </Option>
        ))}
      </Select>
      {help && <HelpText>{help}</HelpText>}
    </Box>
  );
}

/** Labeled multi-line text input. */
export function AreaField({ label, value, onChange, help }: Base<string>) {
  const id = useId();
  return (
    <Box marginBottom="space50">
      <Label htmlFor={id}>{label}</Label>
      <TextArea id={id} value={value} onChange={(e) => onChange(e.target.value)} />
      {help && <HelpText>{help}</HelpText>}
    </Box>
  );
}
