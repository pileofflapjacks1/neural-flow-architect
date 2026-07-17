"""Render human-readable explanations for agent actions."""

from __future__ import annotations

from neural_flow_architect.core.types import ActionProposal, Explanation, WorldSnapshot

_TEMPLATES: dict[str, str] = {
    "ui.set_density": (
        "I adjusted the interface density because your neural engagement signature "
        "is {engagement:.0%} and you are in {state}."
    ),
    "notify.suppress_noncritical": (
        "I suppressed non-critical notifications because your engagement signature is "
        "{engagement:.0%} and you have been in {state} for {minutes:.0f} minutes."
    ),
    "notify.allow_all": (
        "I restored notifications because you appear to be leaving deep engagement "
        "({state}, engagement {engagement:.0%})."
    ),
    "focus.enable": (
        "I enabled focus mode to protect emerging concentration "
        "(engagement {engagement:.0%}, state {state})."
    ),
    "focus.disable": (
        "I disabled focus mode to support a graceful transition out of flow."
    ),
    "iot.lights.dim_for_focus": (
        "I dimmed the lights because your engagement signature is rising "
        "({engagement:.0%}) and ambient support may help sustain flow."
    ),
    "iot.lights.restore": "I restored previous lighting after a flow transition.",
}


class Explainer:
    def render(self, proposal: ActionProposal, snapshot: WorldSnapshot) -> Explanation:
        template = _TEMPLATES.get(
            proposal.tool_id,
            "I ran {action} based on your current estimated flow-related state ({state}).",
        )
        text = template.format(
            action=proposal.tool_id,
            engagement=snapshot.flow.engagement,
            state=snapshot.flow.state.value.replace("_", " "),
            minutes=max(snapshot.flow.minutes_in_state, 0.1),
        )
        return Explanation(
            action=proposal.tool_id,
            text=text,
            because=proposal.causes,
        )
