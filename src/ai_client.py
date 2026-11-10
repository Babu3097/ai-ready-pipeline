"""
ai_client.py - the one place that talks to Claude.

DEMO MODE: if there is no ANTHROPIC_API_KEY in your .env file, the project
runs in demo mode. Nothing is sent anywhere and nothing costs money.
Other files ask `is_demo()` and use a simple built-in stand-in instead.

Try it:   python src/ai_client.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # reads the key from .env - the key never appears in code

MODEL = "claude-haiku-5-5"  # the cheap, fast model (our default)

# ASSUMPTIONS for the cost estimate - check the real prices in the Claude Console.
PRICE_IN_USD_PER_MILLION_TOKENS = 1.00
PRICE_OUT_USD_PER_MILLION_TOKENS = 5.00
USD_TO_GBP = 0.80
BUDGET_GBP = 2.00  # we stop before spending more than this in one run


def is_demo() -> bool:
    """True when there is no API key, so we run without calling Claude."""
    return not os.getenv("ANTHROPIC_API_KEY", "").strip()


class BudgetExceeded(Exception):
    pass


class CostTracker:
    """Counts tokens and works out an approximate cost in pounds."""

    def __init__(self, budget_gbp: float = BUDGET_GBP):
        self.budget_gbp = budget_gbp
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def cost_gbp(self) -> float:
        usd = (
            self.input_tokens * PRICE_IN_USD_PER_MILLION_TOKENS
            + self.output_tokens * PRICE_OUT_USD_PER_MILLION_TOKENS
        ) / 1_000_000
        return usd * USD_TO_GBP

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def check_budget(self) -> None:
        if self.cost_gbp >= self.budget_gbp:
            raise BudgetExceeded(
                f"Stopping: estimated cost £{self.cost_gbp:.2f} reached the £{self.budget_gbp:.2f} limit."
            )


def ask_claude(prompt: str, system: str = "", max_tokens: int = 300,
               tracker: CostTracker = None) -> str:
    """Send one question to Claude and return its text answer."""
    if is_demo():
        raise RuntimeError("Demo mode: no API key set. Check is_demo() before calling ask_claude().")
    import anthropic  # imported here so demo mode works even if the package is missing

    if tracker:
        tracker.check_budget()
    client = anthropic.Anthropic()  # finds the key in the environment by itself
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if tracker:
        tracker.add(response.usage.input_tokens, response.usage.output_tokens)
    return response.content[0].text


if __name__ == "__main__":
    # Phase 0 check: does the connection work?
    if is_demo():
        print("DEMO MODE: no API key found in .env, so nothing was sent to Claude.")
        print("That's fine - everything still runs. Add a key later to use the real thing.")
        sys.exit(0)
    tracker = CostTracker()
    print("Asking Claude a tiny question...")
    print("Claude says:", ask_claude("Say hello in five words.", max_tokens=30, tracker=tracker))
    print(f"Tokens used: {tracker.input_tokens} in, {tracker.output_tokens} out "
          f"(about £{tracker.cost_gbp:.5f})")
