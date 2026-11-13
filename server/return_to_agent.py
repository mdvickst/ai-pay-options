
from server import events
from server.card_parse import spaced
from server.state import CallState
from server.tac_app import agent_relay_options, voice_channel


def success_outcome(amount: float, last4: str | None = None, code: str | None = None) -> str:
    """Spoken sentence for a successful payment."""
    text = f"Thanks, your payment of ${amount:.2f}"
    if last4:
        text += f" on the card ending in {spaced(last4)}"
    text += " was successful."
    if code:
        text += f" Your confirmation code is {spaced(code[-6:])}."
    return text


def failure_outcome() -> str:
    """Spoken sentence for a failed payment."""
    return "Sorry, the payment didn't go through, so nothing was charged."


async def return_to_agent_twiml(call: CallState, outcome: str) -> str:
    """Returns TwiML that reconnects the caller to the agent, greeting with the outcome and recording it in history."""
    greeting = f"{outcome} Is there anything else I can help you with?"
    call.history += [
        {"role": "user", "content": f"[SYSTEM EVENT] The secure payment flow finished. Outcome: {outcome}"},
        {"role": "assistant", "content": greeting},
    ]
    events.publish("call", "Returned to agent", {"outcome": outcome}, call.call_sid)
    return await voice_channel.handle_incoming_call(host_twiml_options=agent_relay_options(greeting))
