import os
import json
import time
from openai import OpenAI, RateLimitError

from models.schemas import ProjectPlan, RequirementAnalysis


class PlannerAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "openai/gpt-oss-120b"

    def plan(self, requirement: RequirementAnalysis) -> ProjectPlan:

        schema_hint = json.dumps(ProjectPlan.model_json_schema(), indent=2)

        prompt = f"""
You are a Software Planning Agent for a PYTHON project (standard library first;
only introduce a third-party package like flask, requests, or pytest if the
requirement genuinely needs it -- e.g. a web app needs flask, a GUI needs
tkinter which is stdlib).

Given the analyzed requirement below, produce a concrete implementation plan.

PROJECT NAME: {requirement.project_name}
DESCRIPTION: {requirement.project_description}

FUNCTIONAL REQUIREMENTS:
{chr(10).join(f"- {r}" for r in requirement.functional_requirements)}

NON-FUNCTIONAL REQUIREMENTS:
{chr(10).join(f"- {r}" for r in requirement.non_functional_requirements)}

ASSUMPTIONS:
{chr(10).join(f"- {a}" for a in requirement.assumptions)}

Respond with ONLY a valid JSON object matching this exact schema (no markdown, no explanation):
{schema_hint}

Produce:
1. modules: high-level Python modules/files needed (e.g. "model", "service", "ui", "cli")
2. entities: each domain concept with its fields (name: type) -- can be an empty list if
   the project has no real data model (e.g. a simple CLI tool)
3. endpoints: only fill this in if the project is a web API/app (method, path, description).
   For a desktop, CLI, or script project, return an empty list -- do NOT invent a REST API
   for something that isn't one.
4. tasks: ordered, atomic development tasks with unique task_id and depends_on referencing
   earlier task_ids. One task should always be "Write unit tests" using pytest, depending on
   the core logic tasks.
5. tech_notes: relevant Python decisions (max 6 short notes, one line each) -- state explicitly
   whether this is a CLI app, a tkinter desktop app, or a flask web app, and which third-party
   packages (if any) are required.

Rules:
- Default to plain Python standard library. Only add a dependency if the requirement can't
  reasonably be met without it.
- Keep entities and endpoints consistent with each other.
- Tasks must be atomic (one file/concern per task) and ordered so dependencies come first.
- Do not invent requirements not implied by the input.
- Keep the response compact - short descriptions, no long prose.
"""

        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert Python software architect and technical planner. Always respond with valid, complete JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                raw = response.choices[0].message.content
                data = json.loads(raw)

                if "tasks" in data:
                    data["tasks"] = [json.loads(t) if isinstance(t, str) else t for t in data["tasks"]]
                if "entities" in data:
                    data["entities"] = [json.loads(e) if isinstance(e, str) else e for e in data["entities"]]
                if "endpoints" in data:
                    data["endpoints"] = [json.loads(ep) if isinstance(ep, str) else ep for ep in data["endpoints"]]

                return ProjectPlan.model_validate(data)

            except RateLimitError as e:
                wait = 2 ** attempt
                print(f"  Planner rate-limited (attempt {attempt}), waiting {wait}s...")
                last_error = e
                time.sleep(wait)
            except Exception as e:
                last_error = e
                print(f"  Planner attempt {attempt} failed ({type(e).__name__}), retrying...")

        raise RuntimeError(f"Planner failed after {max_retries} attempts. Last error: {last_error}")