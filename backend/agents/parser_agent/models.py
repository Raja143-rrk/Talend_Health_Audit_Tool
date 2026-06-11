from pydantic import BaseModel, Field


class TalendComponent(BaseModel):
    id: str | None = None
    name: str
    component_name: str
    disabled: bool = False
    job: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)


class TalendJob(BaseModel):
    id: str | None = None
    name: str
    path: str
    item_type: str = "job_design"
    version: str | None = None
    components: list[TalendComponent] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    source_systems: list[str] = Field(default_factory=list)
    target_systems: list[str] = Field(default_factory=list)
    disabled_components: list[TalendComponent] = Field(default_factory=list)


class TalendProjectInventory(BaseModel):
    project_name: str | None = None
    workspace_path: str
    project_files: list[str] = Field(default_factory=list)
    property_files: list[str] = Field(default_factory=list)
    item_files: list[str] = Field(default_factory=list)
    total_jobs: int = 0
    job_names: list[str] = Field(default_factory=list)
    jobs: list[TalendJob] = Field(default_factory=list)
    components: list[TalendComponent] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    source_systems: list[str] = Field(default_factory=list)
    target_systems: list[str] = Field(default_factory=list)
    disabled_components: list[TalendComponent] = Field(default_factory=list)
    parse_errors: list[str] = Field(default_factory=list)
