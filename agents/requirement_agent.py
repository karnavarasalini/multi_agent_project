import os
import json
from openai import OpenAI

from models.schemas import RequirementAnalysis


class RequirementAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "openai/gpt-oss-120b"

    def analyze(self, user_request: str) -> RequirementAnalysis:

        schema_hint = json.dumps(RequirementAnalysis.model_json_schema(), indent=2)

        prompt = f"""
You are a Requirement Analysis Agent.

Analyze the following software project requirement.

USER REQUEST:
{user_request}

Respond with ONLY a valid JSON object matching this exact schema (no markdown, no explanation):
{schema_hint}

Rules:
- Be precise.
- Stay grounded in the user's request.
- Do not invent unnecessary requirements.
- If there are no clarification questions, return an empty list.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert software requirements analyst. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content
        return RequirementAnalysis.model_validate_json(raw)