from pydantic import BaseModel, Field


class TalendComponent(BaseModel):
    id: str | None = None
    name: str
    component_name: str
    disabled: bool = False
    job: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)


class ContextParameter(BaseModel):
    name: str
    value: str
    prompt: str | None = None
    comment: str | None = None
    encrypted: bool = False


class Connection(BaseModel):
    source_id: str
    target_id: str
    connection_type: str = "FLOW"
    label: str | None = None


class ContextGroup(BaseModel):
    name: str
    parameters: list[ContextParameter] = Field(default_factory=list)
    external_file_path: str | None = None


class TalendJob(BaseModel):
    id: str | None = None
    name: str
    path: str
    item_type: str = "job_design"
    job_type: str = "standalone"
    subjob_name: str | None = None
    version: str | None = None
    components: list[TalendComponent] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    context_groups: list[ContextGroup] = Field(default_factory=list)
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
    context_groups: list[ContextGroup] = Field(default_factory=list)
    source_systems: list[str] = Field(default_factory=list)
    target_systems: list[str] = Field(default_factory=list)
    disabled_components: list[TalendComponent] = Field(default_factory=list)
    parse_errors: list[str] = Field(default_factory=list)
