from dotenv import load_dotenv
load_dotenv()

from requirement_input import get_requirement
from agents.requirement_agent import RequirementAgent
from agents.planner_agent import PlannerAgent
from agents.developer_agent import DeveloperAgent
from agents.file_writer import write_project_files
from agents.tester_agent import TesterAgent
from models.schemas import ProjectState
from agents.debugger_agent import run_debugger_agent

requirement_text = get_requirement()

state = ProjectState(user_request=requirement_text)

# ---------- Requirement Agent ----------
req_agent = RequirementAgent()
state.requirement_analysis = req_agent.analyze(requirement_text)

print("\n========== REQUIREMENT ANALYSIS ==========")
print("\nProject Name:", state.requirement_analysis.project_name)

print("\nFunctional Requirements:")
for item in state.requirement_analysis.functional_requirements:
    print("-", item)

print("\nNon-Functional Requirements:")
for item in state.requirement_analysis.non_functional_requirements:
    print("-", item)

print("\nAssumptions:")
for item in state.requirement_analysis.assumptions:
    print("-", item)

print("\nClarification Questions:")
clarification_answers = []
for item in state.requirement_analysis.clarification_questions:
    print("-", item)
    answer = input("  Your answer (press Enter to skip): ").strip()
    if answer:
        clarification_answers.append(f"{item} -> {answer}")

# Feed the answers into the plan as extra assumptions so the Planner
# Agent actually sees and uses them.
if clarification_answers:
    state.requirement_analysis.assumptions.extend(clarification_answers)

# ---------- Planner Agent ----------
planner = PlannerAgent()
state.plan = planner.plan(state.requirement_analysis)

print("\n========== PROJECT PLAN ==========")
print("\nModules:", state.plan.modules)

print("\nEntities:")
for e in state.plan.entities:
    print(f"- {e.name}: {e.fields}")

print("\nEndpoints:")
for ep in state.plan.endpoints:
    print(f"- {ep.method} {ep.path} - {ep.description}")

print("\nTasks:")
for t in state.plan.tasks:
    deps = f" (depends on {t.depends_on})" if t.depends_on else ""
    print(f"- [{t.task_id}] {t.title}{deps}")

# ---------- Developer Agent ----------
print("\n========== DEVELOPER AGENT ==========")
developer = DeveloperAgent()
state.developer_output = developer.develop(state.plan, state.requirement_analysis.project_name)

print(f"\nGenerated {len(state.developer_output.files)} files:")
for f in state.developer_output.files:
    print("-", f.path)

if state.developer_output.notes:
    print("\nNotes/Failures:")
    for n in state.developer_output.notes:
        print("-", n)

project_root = write_project_files(state.developer_output, state.requirement_analysis.project_name)
state.output_dir = project_root
print(f"\nProject written to: {project_root}")

# ---------- Tester + Debugger ----------
tester = TesterAgent()
state.test_result = tester.test(state.output_dir)
print(f"\n[DEBUG] After first test: passed={state.test_result.passed}, status={state.status}")

while not state.test_result.passed and state.status != "failed":
    print(f"[DEBUG] Loop entered. iteration={state.iteration}, max={state.max_iterations}")
    if state.iteration >= state.max_iterations:
        state.status = "failed"
        print(f"\nMax iterations ({state.max_iterations}) reached.")
        break

    print(f"\nIteration {state.iteration + 1}: tests failed, running Debugger Agent...")
    state = run_debugger_agent(state)
    print(f"[DEBUG] After debugger: status={state.status}, debug_history_len={len(state.debug_history)}")

    state.iteration += 1
    state.test_result = tester.test(state.output_dir)

print(f"[DEBUG] Loop exited. Final: passed={state.test_result.passed}, status={state.status}")

if state.test_result.passed:
    state.status = "success"

print("\n========== DEBUG: RAW TEST OUTPUT ==========")
if state.test_result:
    print(state.test_result.error_summary)
    print("---- RAW OUTPUT (first 1000 chars) ----")
    print(state.test_result.raw_output[:1000])

print("\n========== FINAL STATUS ==========")
print("Status:", state.status)
print("Iterations used:", state.iteration)
if state.test_result:
    print("Tests passed:", state.test_result.passed)