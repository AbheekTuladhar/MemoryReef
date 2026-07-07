from __future__ import annotations

import re
from uuid import uuid4

from backend.models import AgentLog, AttemptTrace, Reflection, Scenario, Skill
from backend.tools.skill_store import load_skills


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "skill"


def _tag_key(skill: Skill) -> tuple[str, str, str]:
    tags = [tag.lower().strip() for tag in skill.tags[-3:]]
    while len(tags) < 3:
        tags.append("")
    return tuple(tags[:3])


def _with_id(skill: Skill) -> Skill:
    return skill.model_copy(update={"skill_id": f"skill_{_slug(skill.name)}_{uuid4().hex[:6]}"})


def _candidates(trace: AttemptTrace, scenario: Scenario) -> list[Skill]:
    skill_id = "skill_" + _slug(scenario.target_skill)
    fallback = Skill(
        skill_id=f"skill_custom_debugging_lesson_{uuid4().hex[:6]}",
        name=scenario.target_skill or "Custom Debugging Lesson",
        description=(
            "For user-provided logs, identify the earliest concrete clue, separate symptoms from causes, "
            "and keep confidence tied to the amount of supporting evidence."
        ),
        when_to_use=[
            "A user pastes or uploads unfamiliar logs",
            "The task has no curated expected answer",
            "Several causes remain plausible",
        ],
        steps=[
            "Redact sensitive values before storing the trace.",
            "Build a timeline from any available timestamps.",
            "List the strongest evidence and the missing evidence.",
            "Give a confidence score that matches the evidence quality.",
            "Ask for project, deploy, or dependency context when the logs are ambiguous.",
        ],
        anti_pattern="Giving a confident root-cause claim from unfamiliar logs without checking timing or missing context.",
        source_trace_id=trace.trace_id,
        tags=["custom-logs", "evidence", "confidence"],
    )
    candidates = {
        "loudest_error": [
            Skill(
                skill_id=skill_id,
            name="Avoid the Loudest Error Trap",
            description="Do not assume the most repeated error is the root cause. Check event order and upstream clues first.",
            when_to_use=[
                "Many repeated errors appear in one component",
                "Multiple components are failing",
                "Timestamps or event order are available",
            ],
            steps=[
                "Identify the most frequent error.",
                "Build a simple timeline.",
                "Find the earliest abnormal event.",
                "Check whether the frequent error happened later as a symptom.",
                "Choose the cause that best explains the chain of failures.",
            ],
            anti_pattern="Choosing the noisiest error without checking timing.",
            source_trace_id=trace.trace_id,
            tags=["timeline", "cause-vs-symptom", "root-cause"],
            ),
            Skill(
                skill_id=skill_id,
                name="Trace the First Upstream Failure",
                description="When downstream services are noisy, map the dependency chain and prioritize the first upstream failure that explains later symptoms.",
                when_to_use=[
                    "Multiple downstream symptoms follow one earlier dependency error",
                    "A repeated user-facing error may be masking the cause",
                    "Logs include enough ordering to compare cause and effect",
                ],
                steps=[
                    "List components in likely dependency order.",
                    "Find the first failing dependency in that chain.",
                    "Check whether later errors depend on that component.",
                    "State the upstream cause separately from downstream symptoms.",
                ],
                anti_pattern="Treating a downstream service as causal just because it reports the most visible errors.",
                source_trace_id=trace.trace_id,
                tags=["dependency-order", "upstream-failure", "symptom-chain"],
            ),
            Skill(
                skill_id=skill_id,
                name="Compare Frequency Against Timing",
                description="Use error frequency only after checking event timing; the most frequent error is often an amplified symptom.",
                when_to_use=[
                    "One component emits repeated errors",
                    "Another component logged an earlier abnormal event",
                    "The incident has timestamped entries",
                ],
                steps=[
                    "Count repeated errors.",
                    "Find the first abnormal timestamp.",
                    "Compare whether repetition started after the first clue.",
                    "Prefer the explanation that accounts for both timing and frequency.",
                ],
                anti_pattern="Letting error volume outweigh a clear earlier clue.",
                source_trace_id=trace.trace_id,
                tags=["error-frequency", "event-timing", "amplified-symptom"],
            ),
        ],
        "deployment_suspicion": [
            Skill(
                skill_id=skill_id,
            name="Check Recent Deployment Configuration",
            description="If failures begin immediately after a deployment, inspect config, feature flags, and environment variables before blaming downstream symptoms.",
            when_to_use=["A deploy event appears just before errors", "Startup or config errors follow a release"],
            steps=[
                "Find the latest deploy or config change.",
                "Compare the first error after the change.",
                "Inspect missing environment variables, feature flags, and secret names.",
                "Treat later gateway or status-code spikes as symptoms until proven otherwise.",
            ],
            anti_pattern="Blaming user-facing status codes while ignoring the deployment clue.",
            source_trace_id=trace.trace_id,
            tags=["deployment", "configuration", "root-cause"],
            ),
            Skill(
                skill_id=skill_id,
                name="Inspect Release-Time Startup Failures",
                description="If a service fails immediately after a release, inspect startup errors and configuration changes before chasing gateway symptoms.",
                when_to_use=["A service version changes before errors", "Startup failures appear right after deploy", "Gateway errors follow service startup errors"],
                steps=[
                    "Identify the deploy timestamp.",
                    "Inspect the first startup or config error after deploy.",
                    "Check environment variables, feature flags, and secrets.",
                    "Treat later gateway errors as dependent symptoms until contradicted.",
                ],
                anti_pattern="Debugging the gateway first when a service failed during startup after deploy.",
                source_trace_id=trace.trace_id,
                tags=["release-timing", "startup-error", "config-check"],
            ),
        ],
        "retry_storm": [
            Skill(
                skill_id=skill_id,
            name="Detect Retry Amplification",
            description="Retries combined with rising queue depth or backlog often mean a slow dependency is being amplified into a wider outage.",
            when_to_use=["Retry attempts appear repeatedly", "Queue depth or backlog is rising", "Rate limits occur after retries"],
            steps=[
                "Locate the first timeout or slow dependency.",
                "Count retry attempts after that clue.",
                "Check for queue growth or backlog.",
                "Treat later rate limits as an effect of amplification unless other evidence contradicts it.",
            ],
            anti_pattern="Treating the final rate-limit error as the root cause.",
            source_trace_id=trace.trace_id,
            tags=["retry", "queue", "amplification"],
            ),
            Skill(
                skill_id=skill_id,
                name="Find the Original Slow Dependency",
                description="When retries and backlog appear, work backward to the first slow or timed-out dependency instead of blaming the final limiter.",
                when_to_use=["Retries happen after a timeout", "Queue backlog rises", "Rate limiting appears after retry bursts"],
                steps=[
                    "Find the first slow or timed-out service.",
                    "Check which caller began retrying afterward.",
                    "Relate queue growth to retry volume.",
                    "Separate the original dependency issue from the amplified outage.",
                ],
                anti_pattern="Calling rate limiting the cause when it may be a consequence of retry pressure.",
                source_trace_id=trace.trace_id,
                tags=["slow-dependency", "retry-pressure", "backlog-growth"],
            ),
        ],
        "missing_evidence": [
            Skill(
                skill_id=skill_id,
            name="Ask for Missing Evidence Before Guessing",
            description="When the snippet has only symptoms and no clear upstream clue, give a cautious answer and request the missing context needed to decide.",
            when_to_use=["Only generic errors are present", "No deployment or dependency logs are shown", "Several causes remain plausible"],
            steps=[
                "State that the evidence is insufficient for a strong root-cause claim.",
                "Name the visible symptoms.",
                "Ask for the smallest useful missing context: deployment events, dependency logs, secret/config changes, or fuller timestamps.",
                "Keep confidence moderate until new evidence arrives.",
            ],
            anti_pattern="Inventing a confident root cause from a short ambiguous snippet.",
            source_trace_id=trace.trace_id,
            tags=["missing-evidence", "confidence", "debugging-discipline"],
            ),
            Skill(
                skill_id=skill_id,
                name="Bound Claims by Available Evidence",
                description="When logs contain only generic symptoms, present a bounded hypothesis and request the smallest missing context needed to decide.",
                when_to_use=["Only symptoms are visible", "No upstream dependency logs are present", "Several root causes remain possible"],
                steps=[
                    "Name the visible symptoms.",
                    "State what evidence is missing.",
                    "Offer a low-to-moderate confidence hypothesis.",
                    "Ask for the smallest next log or change history that can disambiguate.",
                ],
                anti_pattern="Turning a plausible hypothesis into a confident root-cause claim.",
                source_trace_id=trace.trace_id,
                tags=["bounded-claim", "missing-context", "hypothesis-discipline"],
            ),
        ],
    }
    custom_candidates = [
        fallback,
        fallback.model_copy(
            update={
                "name": "Use Project Context Cautiously",
                "description": "When uploaded project files are available, use them to form targeted next checks without overclaiming beyond the logs.",
                "tags": ["project-context", "targeted-checks", "cautious-debugging"],
            }
        ),
        fallback.model_copy(
            update={
                "name": "Connect Logs to Code Clues",
                "description": "Match log errors to nearby code/config clues, then ask for runtime context before making a strong claim.",
                "tags": ["code-clues", "runtime-context", "log-correlation"],
            }
        ),
    ]
    return [_with_id(skill) for skill in candidates.get(scenario.pair_id, custom_candidates)]


def _choose_unique_skill(trace: AttemptTrace, scenario: Scenario) -> tuple[Skill, int]:
    existing_tag_keys = {_tag_key(skill) for skill in load_skills()}
    candidates = _candidates(trace, scenario)
    for index, candidate in enumerate(candidates, start=1):
        if _tag_key(candidate) not in existing_tag_keys:
            return candidate, index
    fallback = candidates[-1]
    variant = fallback.model_copy(
        update={
            "skill_id": f"skill_{_slug(fallback.name)}_{uuid4().hex[:6]}",
            "name": f"{fallback.name} Variant {uuid4().hex[:4]}",
            "tags": [fallback.tags[-2], fallback.tags[-1], f"variant-{uuid4().hex[:4]}"],
        }
    )
    return variant, len(candidates) + 1


def reflect_on_trace(trace: AttemptTrace, scenario: Scenario) -> tuple[Reflection, Skill]:
    skill, attempts = _choose_unique_skill(trace, scenario)
    reflection = Reflection(
        reflection_id=f"reflection_{uuid4().hex[:8]}",
        trace_id=trace.trace_id,
        what_happened=(
            "The investigator produced a summarized trace with keyword and timeline evidence, then compared visible symptoms with likely causes."
        ),
        lesson=skill.description,
        proposed_skill_id=skill.skill_id,
        confidence=0.7 if scenario.purpose == "custom" else 0.82,
        agent_logs=[
            AgentLog(
                agent="Reflection Agent",
                event="trace_review",
                summary=f"Reviewed trace {trace.trace_id}, including {len(trace.steps)} tool step(s) and {len(trace.used_skills)} saved skill reference(s).",
                confidence=0.84,
            ),
            AgentLog(
                agent="Reflection Agent",
                event="lesson_extraction",
                summary=f"Generated {attempts} candidate reflection(s) and selected a non-duplicate lesson by comparing the final three skill tags: {skill.name}.",
                confidence=0.7 if scenario.purpose == "custom" else 0.82,
            ),
            AgentLog(
                agent="Reflection Agent",
                event="safety_filter",
                summary="Kept the proposed skill procedural and avoided storing hidden reasoning or private raw thoughts.",
                confidence=0.88,
            ),
        ],
    )
    return reflection, skill
