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
    "recipe.apply": (
        "I applied the {action} environment recipe because your context and "
        "estimated state ({state}, engagement {engagement:.0%}) suggest it will help."
    ),
    "prepare.context": (
        "I prepared your environment for a likely state change "
        "(engagement {engagement:.0%}, state {state})."
    ),
    "tasks.queue_next": (
        "I queued a gentle next-step suggestion based on a possible task-switch precursor "
        "(engagement {engagement:.0%})."
    ),
}




class Explainer:
    def render(self, proposal: ActionProposal, snapshot: WorldSnapshot) -> Explanation:
        template = _TEMPLATES.get(
            proposal.tool_id,
            "I ran {action} based on your current estimated flow-related state ({state}).",
        )
        recipe = str(proposal.params.get("recipe") or snapshot.context.recipe or "focus")
        text = template.format(
            action=proposal.tool_id if proposal.tool_id != "recipe.apply" else f"{recipe}",
            engagement=snapshot.flow.engagement,
            state=snapshot.flow.state.value.replace("_", " "),
            minutes=max(snapshot.flow.minutes_in_state, 0.1),
        )
        if proposal.tool_id == "recipe.apply":
            text = (
                f"I applied the {recipe} environment recipe because your estimated state "
                f"is {snapshot.flow.state.value.replace('_', ' ')} "
                f"(engagement {snapshot.flow.engagement:.0%})."
            )

        return Explanation(
            action=proposal.tool_id,
            text=text,
            because=proposal.causes,
        )
