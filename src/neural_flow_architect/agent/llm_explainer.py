"""Optional local LLM wording for explanations — summaries only, never raw neural data."""

from __future__ import annotations

import json
from typing import Any

import httpx

from neural_flow_architect.core.types import ActionProposal, Explanation, WorldSnapshot


class LocalLLMExplainer:
    """
    Calls a local OpenAI-compatible endpoint (e.g. Ollama) to rephrase explanations.

    Safety:
    - Off by default
    - Sends only structured state summaries (no raw samples / features arrays)
    - Cloud endpoints require explicit allow_cloud_llm
    - Always falls back to template text on failure
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2",
        allow_cloud: bool = False,
        timeout_sec: float = 2.5,
    ) -> None:
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.allow_cloud = allow_cloud
        self.timeout_sec = timeout_sec
        self.last_error: str | None = None
        self.last_used_llm = False

    def _is_local_url(self) -> bool:
        host = self.base_url.lower()
        return any(
            x in host
            for x in (
                "127.0.0.1",
                "localhost",
                "0.0.0.0",
                "::1",
            )
        )

    def build_summary_payload(
        self, proposal: ActionProposal, snapshot: WorldSnapshot, template_text: str
    ) -> dict[str, Any]:
        """Minimal summary — never include raw neural data."""
        return {
            "action": proposal.tool_id,
            "params": proposal.params,
            "template_explanation": template_text,
            "flow": {
                "state": snapshot.flow.state.value,
                "engagement": round(snapshot.flow.engagement, 3),
                "confidence": round(snapshot.flow.confidence, 3),
                "minutes_in_state": round(snapshot.flow.minutes_in_state, 2),
            },
            "context": {
                "recipe": snapshot.context.recipe,
                "time_of_day": snapshot.context.time_of_day,
                "user_goal": snapshot.context.user_goal,
            },
            "quality_overall": round(snapshot.quality.overall, 3),
        }

    async def rephrase(
        self, proposal: ActionProposal, snapshot: WorldSnapshot, template_text: str
    ) -> str | None:
        self.last_used_llm = False
        self.last_error = None
        if not self.enabled:
            return None
        if not self._is_local_url() and not self.allow_cloud:
            self.last_error = "non-local LLM URL blocked (allow_cloud_llm=false)"
            return None

        payload = self.build_summary_payload(proposal, snapshot, template_text)
        prompt = (
            "You help a BCI user understand why an assistive co-pilot acted. "
            "Rewrite the explanation in one calm, clear sentence. "
            "Do not invent medical claims. Do not mention raw neural data.\n\n"
            f"DATA:\n{json.dumps(payload)}\n\n"
            "Rewritten explanation:"
        )
        try:
            # Ollama native generate API
            url = f"{self.base_url}/api/generate"
            body = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 80},
            }
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.post(url, json=body)
            if resp.status_code >= 300:
                # Try OpenAI-compatible chat
                return await self._openai_compatible(prompt)
            data = resp.json()
            text = str(data.get("response") or "").strip()
            if text:
                self.last_used_llm = True
                return text.split("\n")[0][:400]
            return await self._openai_compatible(prompt)
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            return None

    async def _openai_compatible(self, prompt: str) -> str | None:
        try:
            url = f"{self.base_url}/v1/chat/completions"
            body = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 80,
            }
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.post(url, json=body)
            if resp.status_code >= 300:
                self.last_error = f"LLM HTTP {resp.status_code}"
                return None
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            text = choices[0].get("message", {}).get("content") or ""
            text = str(text).strip()
            if text:
                self.last_used_llm = True
                return text.split("\n")[0][:400]
            return None
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            return None


async def maybe_llm_explain(
    llm: LocalLLMExplainer | None,
    proposal: ActionProposal,
    snapshot: WorldSnapshot,
    template: Explanation,
) -> Explanation:
    if llm is None or not llm.enabled:
        return template
    rewritten = await llm.rephrase(proposal, snapshot, template.text)
    if not rewritten:
        return template
    return Explanation(
        action=template.action,
        text=rewritten,
        because=template.because
        + [{"signal": "wording", "value": "local_llm"}],
        timestamp=template.timestamp,
    )
