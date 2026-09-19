"""The agent's one non-deterministic tool: drafting outreach text.

No LLM API key is provided for this exercise (per the brief), so the default backend is a
documented mock. If a `GROQ_API_KEY` environment variable is present, a real call to Groq's
OpenAI-compatible chat completion endpoint is used instead, behind the exact same interface —
nothing else in the agent graph needs to know or care which backend is active.

This isolation is deliberate: scoring, gating, tiering, and reason codes are all deterministic
and never touch this module. If this tool is slow, down, or wrong, the worklist still gets
built correctly — only the drafted blurb for Hot-tier accounts is affected.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    "You are a sales development assistant at a B2B software company. Given an account's "
    "profile and the specific signals that make it a priority, write a 2-3 sentence outreach "
    "note a rep could use as a starting point for a call or email. Reference at least one "
    "concrete signal by name. Do not invent facts not present in the input. No greeting or "
    "sign-off, just the body."
)


class OutreachDrafter(ABC):
    """Interface: swap the backend without touching the graph or the UI."""

    @abstractmethod
    def draft(self, account: dict, reason_codes: list[str]) -> str:
        ...


class MockOutreachDrafter(OutreachDrafter):
    """Documented stand-in for a real LLM call.

    If this were live, the request would be:
      - system prompt: SYSTEM_PROMPT (above)
      - user input: the account's fields (account_id, account_type, industry,
        employee_count) plus its reason_codes list, formatted as JSON
      - model: a small fast chat model (e.g. Groq's llama-3.1-8b-instant, temperature 0.3,
        max_tokens ~120) — see GroqOutreachDrafter for the real wiring
      - expected output: a 2-3 sentence plain-text outreach blurb, no greeting/sign-off

    This mock does not call an LLM. It builds a templated-but-content-aware blurb directly
    from the real reason codes, so it's not lorem-ipsum filler — but it is deterministic and
    will phrase things identically for identical inputs, which a real model would not.
    """

    def draft(self, account: dict, reason_codes: list[str]) -> str:
        top_signal = reason_codes[0] if reason_codes else "recent activity"
        industry = account.get("industry", "their industry")
        account_type = account.get("account_type", "account")
        if account_type == "Former Customer":
            opener = (
                f"Worth a win-back touch - {top_signal} suggests renewed interest since they "
                f"left."
            )
        else:
            opener = f"Strong outbound candidate - {top_signal}."
        extra = ""
        if len(reason_codes) > 1:
            extra = f" Also notable: {reason_codes[1]}."
        return (
            f"{opener}{extra} Given they're in {industry}, lead with a relevant use case "
            f"rather than a generic intro."
        )


class GroqOutreachDrafter(OutreachDrafter):
    """Real call to Groq's chat completion API. Only used when GROQ_API_KEY is set."""

    def __init__(self, api_key: str, model: str = GROQ_MODEL, timeout: float = 15.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def draft(self, account: dict, reason_codes: list[str]) -> str:
        user_content = (
            f"Account: {account}\nReason codes (why this account is a priority): "
            f"{reason_codes}"
        )
        response = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.3,
                "max_tokens": 120,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


def get_drafter() -> OutreachDrafter:
    """Factory: real Groq call if GROQ_API_KEY is set, documented mock otherwise.

    This is the plug-in point the brief asks for — swapping the mock for a real call is a
    one-line env var change, nothing else in the codebase changes.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        return GroqOutreachDrafter(api_key=api_key)
    return MockOutreachDrafter()
