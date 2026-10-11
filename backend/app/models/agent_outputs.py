from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator

class StepDefinition(BaseModel):
    id: str = Field(description="Unique ID for the step")
    type: Literal["research", "data", "code"] = Field(
        default="research",
        description="Executable step type. Critic/report/repair are orchestrator-controlled.",
    )
    title: str = Field(default="Step", description="Title of the step")
    description: str = Field(default="", description="Detailed description of what the step should do")
    depends_on: List[str] = Field(default_factory=list, description="IDs of steps this step depends on")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for the step")

    @field_validator("input_data", mode="before")
    @classmethod
    def normalize_input_data(cls, v: Any) -> dict:
        if isinstance(v, str):
            return {"query": v, "description": v}
        elif isinstance(v, dict):
            return v
        return {}

    @field_validator("depends_on", mode="before")
    @classmethod
    def normalize_depends_on(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []

class PlannerOutput(BaseModel):
    steps: List[StepDefinition] = Field(default_factory=list, description="List of steps to execute")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the plan")
    rationale: str = Field(default="", description="Reasoning behind the chosen plan")

class CitationDefinition(BaseModel):
    title: str = Field(default="", description="Title of the source")
    url: str = Field(default="", description="URL or local source reference")
    type: str = Field(default="web", description="Source type: web, paper, dataset, file, or code")
    excerpt: str = Field(default="", description="Relevant passage or claim from the source")
    file_id: Optional[str] = Field(default=None, description="Local knowledge-base file ID")
    page_number: Optional[int] = Field(default=None, ge=1, description="Source page for paginated local documents")
    chunk_id: Optional[str] = Field(default=None, description="RAG chunk ID used as evidence")

class ResearchOutput(BaseModel):
    summary: str = Field(default="", description="Comprehensive summary of findings")
    key_findings: List[str] = Field(default_factory=list, description="List of key findings")
    citations: List[CitationDefinition] = Field(default_factory=list, description="List of citations for every claim")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the research findings")
    gaps: List[str] = Field(default_factory=list, description="Areas where more research is needed")

    @field_validator("key_findings", "gaps", mode="before")
    @classmethod
    def normalize_research_lists(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []

class DataOutput(BaseModel):
    datasets_found: List[Dict[str, Any]] = Field(default_factory=list, description="List of datasets found and used")
    analysis: str = Field(default="", description="Analysis of the data")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Key statistics extracted")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the data analysis")

class CodeOutput(BaseModel):
    code: str = Field(default="", description="The code generated or executed")
    explanation: str = Field(default="", description="Explanation of what the code does")
    execution_result: str = Field(default="", description="Result of code execution if any")
    success: bool = Field(default=True, description="Whether the code execution was successful")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the code correctness")

class CriticOutput(BaseModel):
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the critique")
    quality_score: float = Field(default=4.0, ge=0.0, le=5.0, description="Quality score from 0 to 5")
    issues: List[str] = Field(default_factory=list, description="List of issues found in the output")
    suggestions: List[str] = Field(default_factory=list, description="List of suggestions for improvement")
    verdict: str = Field(default="pass", description="Verdict (e.g. 'pass', 'fail', 'needs_revision')")
    feedback: str = Field(default="", description="Detailed feedback explanation")

    @field_validator("feedback", mode="before")
    @classmethod
    def normalize_feedback(cls, v: Any) -> str:
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return str(v) if v is not None else ""

    @field_validator("issues", "suggestions", mode="before")
    @classmethod
    def normalize_string_list(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, dict):
                    msg = item.get("description") or item.get("message") or item.get("issue") or str(item)
                    res.append(msg)
                elif isinstance(item, str):
                    res.append(item)
                else:
                    res.append(str(item))
            return res
        elif isinstance(v, str):
            return [v]
        return []

class RepairOutput(BaseModel):
    root_cause: str = Field(default="", description="The identified root cause of the failure")
    fix_description: str = Field(default="", description="Description of how the issue was fixed")
    corrected_output: Dict[str, Any] = Field(default_factory=dict, description="The full corrected output")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the repair")

class MemoryNodeDefinition(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    type: Literal["topic", "entity", "technology", "concept"] = "topic"
    description: str = Field(default="", max_length=500)


class MemoryEdgeDefinition(BaseModel):
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)
    relation: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    strength: float = Field(default=0.7, ge=0.0, le=1.0)


class MemoryOutput(BaseModel):
    nodes: List[MemoryNodeDefinition] = Field(default_factory=list, max_length=15)
    edges: List[MemoryEdgeDefinition] = Field(default_factory=list, max_length=40)
    summary: str = Field(default="", max_length=1000)


class ReportSection(BaseModel):
    title: str = Field(default="Section", description="Section title")
    content: str = Field(default="", description="Section content")

class ReportOutput(BaseModel):
    title: str = Field(default="Research Report", description="Report title")
    summary: str = Field(default="", description="Executive summary")
    content: str = Field(default="", description="Full markdown content")
    sections: List[ReportSection] = Field(default_factory=list, description="Report sections")
    citations: List[CitationDefinition] = Field(default_factory=list, description="List of all citations used")
    key_findings: List[str] = Field(default_factory=list, description="Key findings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations based on findings")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the report quality")

    @field_validator("key_findings", "recommendations", mode="before")
    @classmethod
    def normalize_report_lists(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []
