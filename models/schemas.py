from pydantic import BaseModel, Field
from typing import List, Optional


class RequirementAnalysis(BaseModel):
    project_name: str
    project_description: str
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    assumptions: List[str]
    clarification_questions: List[str]


class Task(BaseModel):
    task_id: str
    title: str
    description: str
    depends_on: List[str] = Field(default_factory=list)


class Endpoint(BaseModel):
    method: str          # GET, POST, PUT, DELETE
    path: str            # /api/students
    description: str


class Entity(BaseModel):
    name: str
    fields: List[str]    # e.g. ["id: Long", "name: String", "email: String"]


class ProjectPlan(BaseModel):
    modules: List[str]
    entities: List[Entity]
    endpoints: List[Endpoint]
    tasks: List[Task]
    tech_notes: List[str] = Field(default_factory=list)   # e.g. "Use Spring Data JPA", "H2 for dev"


class GeneratedFile(BaseModel):
    path: str            # relative path e.g. "src/main/java/.../StudentController.java"
    content: str


class DeveloperOutput(BaseModel):
    files: List[GeneratedFile]
    notes: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    raw_output: str
    error_summary: Optional[str] = None


class CodeFix(BaseModel):
    file_path: str
    updated_content: str
    explanation: str
    root_cause: Optional[str] = None
    confidence: str = "high"


class DebugResult(BaseModel):
    root_cause: str
    fixes: List[CodeFix]
    confidence: str        # "high" | "medium" | "low"


class ProjectState(BaseModel):
    """Shared memory object passed through every agent."""
    user_request: str
    requirement_analysis: Optional[RequirementAnalysis] = None
    plan: Optional[ProjectPlan] = None
    developer_output: Optional[DeveloperOutput] = None
    test_result: Optional[TestResult] = None
    debug_history: List[DebugResult] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    status: str = "in_progress"   # "in_progress" | "success" | "failed"
    output_dir: str = "output/generated-project"