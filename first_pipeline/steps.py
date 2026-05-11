"""First pipeline: one programmatic step feeding one agent step.

The deterministic step builds a research brief from a topic. The agent step
takes that brief, runs research via a Poolside agent, and returns findings.

This is the canonical orchestration pattern: programmatic steps prepare
structured context, agent steps reason over it, and the next programmatic
step (not included here, but you should add one for production) validates
the output.
"""

import json
import os
from typing import Annotated

from pydantic import BaseModel

from bridge_sdk import Pipeline, step_result
from bridge_sdk.bridge_execution_client import BridgeExecutionClient


pipeline = Pipeline(
    name="first_pipeline",
    description="Programmatic research brief feeding an agent investigation",
)


# Models

class TopicInput(BaseModel):
    topic: str


class ResearchBrief(BaseModel):
    topic: str
    questions: list[str]
    output_file: str


class AgentFindings(BaseModel):
    session_id: str
    summary: str
    raw_output: dict


# Step 1: deterministic

@pipeline.step
def build_research_brief(input_data: TopicInput) -> ResearchBrief:
    """Build a structured brief from a topic. No LLM, no judgment.

    In a real pipeline this is where you would fetch tickets, query a database,
    pull from a CMDB, etc. Pure data assembly.
    """
    questions = [
        f"What is the current state of {input_data.topic}?",
        f"What are the top three risks associated with {input_data.topic}?",
        f"What is one concrete next step for {input_data.topic}?",
    ]
    return ResearchBrief(
        topic=input_data.topic,
        questions=questions,
        output_file="/tmp/agent_findings.json",
    )


# Step 2: agent

PROMPT_TEMPLATE = """You are a research analyst. Investigate the topic below and
answer each question concisely.

## Topic
{topic}

## Questions
{questions}

## Required Output
You MUST write a JSON file to {output_file} using the write tool. Use this
exact structure:

{{
    "topic": "{topic}",
    "answers": [
        {{"question": "...", "answer": "..."}}
    ],
    "summary": "two-sentence executive summary"
}}

Do not include anything else in the file. Do not skip the write tool call.
"""


@pipeline.step(metadata={"type": "agent"})
def investigate(
    input_data: TopicInput,
    brief: Annotated[ResearchBrief, step_result(build_research_brief)],
) -> AgentFindings:
    """Run an agent against the brief and parse the structured result."""
    prompt = PROMPT_TEMPLATE.format(
        topic=brief.topic,
        questions="\n".join(f"- {q}" for q in brief.questions),
        output_file=brief.output_file,
    )

    with BridgeExecutionClient() as client:
        _, session_id, _ = client.start_agent(
            prompt=prompt,
            agent_name=os.environ.get("POOLSIDE_AGENT_NAME", "starter-agent"),
        )

    try:
        with open(brief.output_file, "r") as f:
            raw = json.load(f)
        summary = raw.get("summary", "")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raw = {"error": str(e)}
        summary = f"Failed to parse agent output: {e}"

    return AgentFindings(
        session_id=session_id,
        summary=summary,
        raw_output=raw,
    )
