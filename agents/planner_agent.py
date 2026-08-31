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
You are a Software Planning Agent for a JAVA SPRING BOOT project, built with Maven.
The generated project must ALWAYS be Java/Spring Boot -- never Python, Flask, or any
other language/stack, regardless of how the requirement is phrased.

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
1. modules: high-level Spring Boot layers/packages needed, using these exact names where
   applicable: "pom", "entity", "repository", "service", "controller", "dto", "config",
   "exception". Always include "pom" as a module.
2. entities: each domain concept with its fields as "name: JavaType" (e.g. "id: Long",
   "name: String", "email: String") -- use proper Java types (Long, String, Integer,
   Boolean, LocalDate, etc.), not Python types.
3. endpoints: REST endpoints (method, path, description) following Spring MVC conventions
   (e.g. GET /api/students, POST /api/students). Almost every Spring Boot project should
   have at least basic CRUD endpoints unless it's explicitly not a web API.
4. tasks: ordered, atomic development tasks with unique task_id and depends_on referencing
   earlier task_ids. MUST include, in dependency order:
   - one task to generate "pom.xml" (Maven build file) with spring-boot-starter-web,
     spring-boot-starter-data-jpa, spring-boot-starter-validation, an H2 or MySQL driver,
     and spring-boot-starter-test as dependencies
   - one task to generate "src/main/resources/application.properties"
   - one task per Entity class (JPA @Entity)
   - one task per Repository interface (extends JpaRepository)
   - one task per Service class
   - one task per REST Controller (@RestController)
   - one final task "Write JUnit tests" (JUnit 5 + Mockito), depending on the
     service/controller tasks
5. tech_notes: relevant Spring Boot decisions (max 6 short notes, one line each) -- state
   the Spring Boot version assumption (e.g. "Spring Boot 3.x, Java 17+"), the build tool
   ("Maven"), the database ("H2 in-memory for dev" or as specified), and any other
   third-party dependencies required (e.g. JWT library, Lombok).

Rules:
- The output is ALWAYS Java/Spring Boot. Do not produce Python modules, Flask routes,
  requirements.txt, or any non-Java tooling under any circumstances.
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
                        {"role": "system", "content": "You are an expert Java Spring Boot software architect and technical planner. Always respond with valid, complete JSON only. You never plan Python or Flask output."},
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