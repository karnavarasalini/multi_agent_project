"""
Celene backend server
----------------------
Exposes your multi-agent pipeline (Requirement -> Planner -> Developer -> Debugger)
as a local HTTP API that celene.html can call.

Run it:
    pip install fastapi uvicorn
    python server.py

Then open celene.html in your browser. Its "Backend Endpoint" field should be:
    http://localhost:8000/generate
"""

import traceback
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


class GenerateRequest(BaseModel):
    prompt: str


def run_celene_pipeline(requirement_text: str) -> str:
    """
    Runs the full Requirement -> Planner -> Developer -> Tester -> Debugger
    pipeline (same flow as main.py) against a plain-English requirement,
    and returns a text summary + the generated files, ready to display and
    download from Celene's frontend.

    NOTE: unlike main.py, this does NOT prompt interactively for clarification
    answers (there's no terminal in a web request) — clarification questions
    are logged but skipped, and the Requirement Agent's own assumptions are
    used as-is.
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
    if state.test_result:
        lines.append(f"Tests passed: {state.test_result.passed}")
        if state.test_result.error_summary:
            lines.append(f"\nTest summary:\n{state.test_result.error_summary}")
    lines.append(f"\nProject written to: {project_root}")

    lines.append(f"\nGenerated {len(state.developer_output.files)} files:")
    for f in state.developer_output.files:
        lines.append(f"\n{'=' * 60}\nFILE: {f.path}\n{'=' * 60}\n{f.content}")

    return "\n".join(lines)


@app.post("/generate")
def generate(req: GenerateRequest):
    try:
        result = run_celene_pipeline(req.prompt)
        return {"result": result}
    except Exception as e:
        # Surface the error text so it shows up in Celene's output panel
        return {"result": f"ERROR: {e}\n\n{traceback.format_exc()}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)