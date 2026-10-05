from pydantic import BaseModel

class TaskTemplate(BaseModel):
    title: str
    description: str
    suggested_budget: float
    suggested_tags: list[str]
    example_prompts: list[str]

class TaskTemplateResponse(TaskTemplate):
    id: str
