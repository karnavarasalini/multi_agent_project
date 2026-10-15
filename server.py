"""
Celene backend server
----------------------
Two-step flow for celene.html:

  1. POST /analyze   -> runs only the Requirement Agent, returns the requirement
                        analysis (incl. clarification questions) so the page can show it.
  2. POST /generate  -> runs the full pipeline (Requirement -> Planner -> Developer ->
                        Tester -> Debugger) using the original prompt PLUS the user's
                        answers and suggestions.

Run it:
    pip install fastapi uvicorn
    python server.py

In celene.html the "Backend Endpoint" field stays:
    http://localhost:8000/generate
(the page derives /analyze from it).
"""

import os
import re
import traceback
from typing import List

from dotenv import load_dotenv
load_dotenv()  # type: ignore

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.requirement_agent import RequirementAgent
from agents.planner_agent import PlannerAgent
from agents.developer_agent import DeveloperAgent
from agents.file_writer import write_project_files
from agents.tester_agent import TesterAgent
from agents.debugger_agent import run_debugger_agent
from models.schemas import ProjectState

app = FastAPI()

# Allow the HTML file (opened via file:// or localhost) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    prompt: str


class QA(BaseModel):
    question: str
    answer: str = ""


class GenerateRequest(BaseModel):
    prompt: str
    answers: List[QA] = []       # answers to the clarification questions
    suggestions: str = ""        # free-text extra requirements from the user


# ---------------------------------------------------------------------------
# Small-talk check ("hi", "hello", "thanks", ...) so the pipeline
# doesn't run for a greeting.
# ---------------------------------------------------------------------------
SMALL_TALK_WORDS = {
    "hi", "hii", "hiii", "hello", "hey", "heyy", "hola", "yo", "sup",
    "good", "morning", "afternoon", "evening", "night",
    "thanks", "thank", "you", "thx", "ok", "okay", "cool", "nice",
    "help", "who", "are", "what", "can", "do", "how", "is", "it", "going",
    "there", "celene", "bye", "test", "testing",
}

GREETING_REPLY = (
    "Hi! \U0001F44B I'm Celene.\n\n"
    "What would you like me to build today? Describe the project and I'll "
    "show you the requirements first, then build it once you confirm.\n\n"
    "Example: \"Create a REST API for managing books with CRUD endpoints "
    "and validation.\""
)


def is_small_talk(text: str) -> bool:
    cleaned = re.sub(r"[^a-z\s]", " ", text.lower())
    words = cleaned.split()
    if not words:
        return True
    return all(w in SMALL_TALK_WORDS for w in words)


# ---------------------------------------------------------------------------
# pom.xml fix. Maven cannot resolve a ${property} in <parent><version>
# (parent is resolved before <properties> are read). Replace it with the
# literal value from <properties>, or 3.2.0 if the property is missing.
# ---------------------------------------------------------------------------
def fix_pom_parent_version(pom_text: str) -> str:
    parent_match = re.search(r"<parent>.*?</parent>", pom_text, flags=re.DOTALL)
    if not parent_match:
        return pom_text
    parent_block = parent_match.group(0)

    ver_match = re.search(r"<version>\s*\$\{([^}]+)\}\s*</version>", parent_block)
    if not ver_match:
        return pom_text  # already a literal version

    prop_name = ver_match.group(1)
    prop_match = re.search(
        rf"<{re.escape(prop_name)}>\s*([^<$]+?)\s*</{re.escape(prop_name)}>",
        pom_text,
    )
    literal = prop_match.group(1) if prop_match else "3.2.0"

    new_parent = parent_block.replace(ver_match.group(0), f"<version>{literal}</version>")
    return pom_text.replace(parent_block, new_parent)


def fix_generated_pom(project_root: str, developer_output) -> None:
    """Fix pom.xml on disk and in the file list shown to the user."""
    pom_path = os.path.join(project_root, "pom.xml")
    if os.path.exists(pom_path):
        with open(pom_path, "r", encoding="utf-8") as fh:
            original = fh.read()
        fixed = fix_pom_parent_version(original)
        if fixed != original:
            with open(pom_path, "w", encoding="utf-8") as fh:
                fh.write(fixed)

    for f in developer_output.files:
        if str(f.path).replace("\\", "/").endswith("pom.xml"):
            f.content = fix_pom_parent_version(f.content)


# ---------------------------------------------------------------------------
# Combine prompt + answers + suggestions into one requirement text
# ---------------------------------------------------------------------------
def build_enriched_request(req: GenerateRequest) -> str:
    parts = [req.prompt.strip()]

    answered = [qa for qa in req.answers if qa.answer.strip()]
    if answered:
        parts.append("\nClarifications from the user:")
        for qa in answered:
            parts.append(f"- Q: {qa.question}\n  A: {qa.answer.strip()}")

    if req.suggestions.strip():
        parts.append(
            "\nAdditional requirements and suggestions from the user:\n"
            + req.suggestions.strip()
        )

    return "\n".join(parts)


def run_celene_pipeline(requirement_text: str) -> str:
    """
    Runs the full Requirement -> Planner -> Developer -> Tester -> Debugger
    pipeline (same flow as main.py) against a plain-English requirement,
    and returns a text summary + the generated files, ready to display and
    download from Celene's frontend.
    """
    state = ProjectState(user_request=requirement_text)

    # ---------- Requirement Agent ----------
    req_agent = RequirementAgent()
    state.requirement_analysis = req_agent.analyze(requirement_text)

    # ---------- Planner Agent ----------
    planner = PlannerAgent()
    state.plan = planner.plan(state.requirement_analysis)

    # ---------- Developer Agent ----------
    developer = DeveloperAgent()
    state.developer_output = developer.develop(
        state.plan, state.requirement_analysis.project_name
    )

    project_root = write_project_files(
        state.developer_output, state.requirement_analysis.project_name
    )
    state.output_dir = project_root

    # Repair pom.xml parent version before Maven runs
    fix_generated_pom(project_root, state.developer_output)

    # ---------- Tester + Debugger loop ----------
    tester = TesterAgent()
    state.test_result = tester.test(state.output_dir)

    while not state.test_result.passed and state.status != "failed":
        if state.iteration >= state.max_iterations:
            state.status = "failed"
            break
        state = run_debugger_agent(state)
        state.iteration += 1
        state.test_result = tester.test(state.output_dir)

    if state.test_result.passed:
        state.status = "success"

    # ---------- Build the text response for the frontend ----------
    lines = []
    lines.append(f"Project: {state.requirement_analysis.project_name}")
    lines.append(f"Status: {state.status}")
    lines.append(f"Iterations used: {state.iteration}")

    ra = state.requirement_analysis
    lines.append(f"\n{'=' * 60}\nREQUIREMENTS\n{'=' * 60}")
    lines.append(ra.model_dump_json(indent=2))

    if state.test_result:
        lines.append(f"Tests passed: {state.test_result.passed}")
        if state.test_result.error_summary:
            lines.append(f"\nTest summary:\n{state.test_result.error_summary}")
    lines.append(f"\nProject written to: {project_root}")

    lines.append(f"\nGenerated {len(state.developer_output.files)} files:")
    for f in state.developer_output.files:
        lines.append(f"\n{'=' * 60}\nFILE: {f.path}\n{'=' * 60}\n{f.content}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 1: analyze only (fast, one LLM call)
# ---------------------------------------------------------------------------
@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        if is_small_talk(req.prompt):
            return {"type": "greeting", "message": GREETING_REPLY}

        analysis = RequirementAgent().analyze(req.prompt)
        return {"type": "analysis", "analysis": analysis.model_dump()}
    except Exception as e:
        return {"type": "error", "message": f"{e}\n\n{traceback.format_exc()}"}


# ---------------------------------------------------------------------------
# Step 2: build (slow: planner + developer + tester/debugger loop)
# ---------------------------------------------------------------------------
@app.post("/generate")
def generate(req: GenerateRequest):
    try:
        if is_small_talk(req.prompt):
            return {"result": GREETING_REPLY}

        enriched = build_enriched_request(req)
        result = run_celene_pipeline(enriched)
        return {"result": result}
    except Exception as e:
        # Surface the error text so it shows up in Celene's output panel
        return {"result": f"ERROR: {e}\n\n{traceback.format_exc()}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)