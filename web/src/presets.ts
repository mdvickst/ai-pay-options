import type { PayPrompt } from "./api";

const p = (field: string, error_type: string, say: string, extra: Partial<PayPrompt> = {}): PayPrompt => ({
  field,
  error_type,
  attempt: "",
  card_type: "",
  require_matching_inputs: false,
  says: [say],
  ...extra,
});

const VM = { card_type: "visa mastercard" };
const AMEX = { card_type: "amex" };

/** <Pay> prompt presets based on the Twilio <Prompt> docs' example usage. */
export const PRESETS: Record<string, { label: string; prompts: PayPrompt[] }> = {
  none: { label: "Twilio default prompts (no <Prompt>)", prompts: [] },
  docs_credit_card: {
    label: "Docs example: credit card (16 prompts)",
    prompts: [
      p("payment-card-number", "", "Please enter your credit card number, followed by the pound key."),
      p("payment-card-number", "timeout", "You didn't enter anything. Please enter your credit card number, followed by the pound key."),
      p("payment-card-number", "invalid-card-number", "That card number isn't valid. Please check the number and enter it again, followed by the pound key."),
      p("payment-card-number", "invalid-card-type", "We accept Visa, Mastercard, and American Express. Please enter one of those cards, followed by the pound key."),
      p("expiration-date", "", "Please enter your card's expiration date, two digits for the month and two for the year."),
      p("expiration-date", "timeout", "You didn't enter an expiration date. Please enter it as month and year, for example 0 7 2 8."),
      p("expiration-date", "invalid-date", "That date isn't valid. Please enter the month and year, for example 0 7 2 8."),
      p("security-code", "", "Please enter the three digit security code on the back of your card.", VM),
      p("security-code", "timeout", "You didn't enter a security code. Please enter the three digits on the back of your card.", VM),
      p("security-code", "invalid-security-code", "That code isn't valid. Please enter the three digits on the back of your card.", VM),
      p("security-code", "", "Please enter the four digit security code on the front of your card.", AMEX),
      p("security-code", "timeout", "You didn't enter a security code. Please enter the four digits on the front of your card.", AMEX),
      p("security-code", "invalid-security-code", "That code isn't valid. Please enter the four digits on the front of your card.", AMEX),
      p("postal-code", "", "Please enter your five digit billing zip code."),
      p("postal-code", "timeout", "You didn't enter a zip code. Please enter the five digits of your billing zip code."),
      p("payment-processing", "", "Thank you. Please wait while we process your payment."),
    ],
  },
  docs_ach: {
    label: "Docs example: ACH (set Payment method to ach-debit)",
    prompts: [
      p("bank-routing-number", "", "Please enter your bank's nine digit routing number."),
      p("bank-routing-number", "timeout", "You didn't enter a routing number. Please enter the nine digit routing number."),
      p("bank-routing-number", "invalid-bank-routing-number", "That routing number isn't valid. Please enter it again."),
      p("bank-account-number", "", "Please enter your bank account number, followed by the pound key."),
      p("bank-account-number", "timeout", "You didn't enter an account number. Please enter it now, followed by the pound key."),
      p("payment-processing", "", "Thank you. Please wait while we process your payment."),
    ],
  },
  attempt_escalation: {
    label: "Attempt-based escalation",
    prompts: [
      p("payment-card-number", "", "Please enter your card number, followed by pound.", { attempt: "1" }),
      p("payment-card-number", "", "Let's try that again. Enter the 15 or 16 digit number on the front of your card, then press pound.", { attempt: "2 3" }),
      p("payment-card-number", "invalid-card-number", "That number didn't work. Check each digit and try once more.", { attempt: "2" }),
      p("payment-card-number", "timeout", "Take your time. Enter your card number whenever you're ready, then press pound."),
    ],
  },
};
