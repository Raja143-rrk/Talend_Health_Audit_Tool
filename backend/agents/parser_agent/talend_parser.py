from pathlib import Path
from xml.etree.ElementTree import Element, ParseError

from backend.agents.parser_agent.models import (
    Connection,
    ContextGroup,
    ContextParameter,
    TalendComponent,
    TalendJob,
    TalendProjectInventory,
)
from backend.agents.parser_agent.xml_utils import (
    bool_attr,
    first_attr,
    iter_by_local_name,
    local_name,
    parse_xml_file,
)
from backend.core.logging import get_logger

SOURCE_HINTS = (
    "input",
    "fileinput",
    "dbinput",
    "salesforceinput",
    "restclient",
    "ftpget",
    "s3get",
    "consumer",
)

TARGET_HINTS = (
    "output",
    "fileoutput",
    "dboutput",
    "salesforceoutput",
    "restrequest",
    "ftpput",
    "s3put",
    "producer",
)

SYSTEM_HINTS = {
    "oracle": "Oracle",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mssql": "MS SQL Server",
    "sqlserver": "MS SQL Server",
    "snowflake": "Snowflake",
    "redshift": "Redshift",
    "s3": "Amazon S3",
    "salesforce": "Salesforce",
    "rest": "REST API",
    "ftp": "FTP",
    "kafka": "Kafka",
    "file": "File",
}

JOB_DESIGN_ITEM_TYPES = {"ProcessItem"}
EXCLUDED_JOB_COMPONENTS = {"tPrejob", "tPostjob"}
EXCLUDED_JOB_COMPONENTS_NORMALIZED = {
    component.lower() for component in EXCLUDED_JOB_COMPONENTS
}

logger = get_logger(__name__)


class TalendParser:
    def parse_workspace(self, workspace_path: str | Path) -> TalendProjectInventory:
        workspace = Path(workspace_path)
        if not workspace.exists() or not workspace.is_dir():
            raise FileNotFoundError(f"Talend workspace does not exist: {workspace}")

        project_files = sorted(workspace.rglob("*.project"))
        property_files = sorted(workspace.rglob("*.properties"))
        item_files = sorted(workspace.rglob("*.item"))

        inventory = TalendProjectInventory(
            workspace_path=str(workspace),
            project_files=[str(path) for path in project_files],
            property_files=[str(path) for path in property_files],
            item_files=[str(path) for path in item_files],
        )

        self._parse_project_files(project_files, inventory)
        property_metadata = self._parse_property_files(property_files, inventory)

        for item_file in item_files:
            try:
                job = self._parse_item_file(item_file, property_metadata.get(item_file.stem, {}))
                if job is None:
                    continue
                logger.info(
                    "[COUNT-DEBUG] Detected job: name=%s path=%s components=%s",
                    job.name,
                    job.path,
                    len(job.components),
                )
                inventory.jobs.append(job)
                inventory.components.extend(job.components)
                inventory.contexts.extend(job.contexts)
                inventory.context_groups.extend(job.context_groups)
                inventory.source_systems.extend(job.source_systems)
                inventory.target_systems.extend(job.target_systems)
                inventory.disabled_components.extend(job.disabled_components)
            except (ParseError, ValueError, OSError) as exc:
                inventory.parse_errors.append(f"{item_file}: {exc}")

        inventory.contexts = sorted(set(inventory.contexts))
        inventory.source_systems = sorted(set(inventory.source_systems))
        inventory.target_systems = sorted(set(inventory.target_systems))
        inventory.job_names = sorted(job.name for job in inventory.jobs)
        inventory.total_jobs = len(inventory.job_names)
        self._classify_jobs(inventory)
        logger.info(
            "[COUNT-DEBUG] Final parser counts: total_jobs=%s job_names=%s total_components=%s",
            inventory.total_jobs,
            inventory.job_names,
            len(inventory.components),
        )
        return inventory

    def _classify_jobs(self, inventory: TalendProjectInventory) -> None:
        called_jobs: set[str] = set()
        for job in inventory.jobs:
            for comp in job.components:
                if comp.component_name == "tRunJob":
                    subjob = comp.parameters.get("PROCESS") or ""
                    if subjob:
                        called_jobs.add(subjob)

        for job in inventory.jobs:
            has_trunjob = any(c.component_name == "tRunJob" for c in job.components)
            is_called = job.name in called_jobs
            if has_trunjob and is_called:
                job.job_type = "master"
                job.subjob_name = job.name
            elif has_trunjob:
                job.job_type = "master"
            elif is_called:
                job.job_type = "subjob"
                job.subjob_name = job.name
            else:
                job.job_type = "standalone"

    def _parse_project_files(
        self,
        project_files: list[Path],
        inventory: TalendProjectInventory,
    ) -> None:
        for project_file in project_files:
            try:
                root = parse_xml_file(project_file)
                inventory.project_name = (
                    first_attr(root, "label", "name", "technicalLabel")
                    or self._first_text(root, "label", "name", "technicalLabel")
                    or inventory.project_name
                )
            except (ParseError, OSError) as exc:
                inventory.parse_errors.append(f"{project_file}: {exc}")

    def _parse_property_files(
        self,
        property_files: list[Path],
        inventory: TalendProjectInventory,
    ) -> dict[str, dict[str, str | None]]:
        metadata: dict[str, dict[str, str | None]] = {}
        for property_file in property_files:
            try:
                root = parse_xml_file(property_file)
                property_node = self._first_element(root, "Property")
                item_node = self._first_item_element(root)
                label = (
                    first_attr(property_node, "label", "displayName") if property_node is not None else None
                )
                version = first_attr(property_node, "version") if property_node is not None else None
                metadata[property_file.stem] = {
                    "id": first_attr(property_node, "id") if property_node is not None else None,
                    "name": label or property_file.stem,
                    "version": version,
                    "item_type": local_name(item_node.tag) if item_node is not None else None,
                }
            except (ParseError, OSError) as exc:
                inventory.parse_errors.append(f"{property_file}: {exc}")
        return metadata

    def _parse_item_file(
        self,
        item_file: Path,
        metadata: dict[str, str | None],
    ) -> TalendJob | None:
        root = parse_xml_file(item_file)
        item_type = metadata.get("item_type") or self._item_type(root)
        if item_type not in JOB_DESIGN_ITEM_TYPES:
            logger.info(
                "[COUNT-DEBUG] Ignored item: path=%s item_type=%s reason=not_talend_job_design",
                item_file,
                item_type or "unknown",
            )
            return None

        job_name = metadata.get("name") or item_file.stem
        components = self._parse_components(root, job_name=job_name, item_file=item_file)
        connections = self._parse_connections(root)
        contexts = self._parse_contexts(root)
        context_groups = self._parse_context_groups(root)

        source_systems = sorted(
            {
                self._detect_system(component.component_name)
                for component in components
                if self._is_source_component(component.component_name)
            }
            - {None}
        )
        target_systems = sorted(
            {
                self._detect_system(component.component_name)
                for component in components
                if self._is_target_component(component.component_name)
            }
            - {None}
        )
        disabled_components = [component for component in components if component.disabled]

        return TalendJob(
            id=metadata.get("id"),
            name=job_name,
            path=str(item_file),
            item_type="job_design",
            version=metadata.get("version"),
            components=components,
            connections=connections,
            contexts=contexts,
            context_groups=context_groups,
            source_systems=source_systems,
            target_systems=target_systems,
            disabled_components=disabled_components,
        )

    def _parse_components(
        self,
        root: Element,
        job_name: str,
        item_file: Path,
    ) -> list[TalendComponent]:
        components: list[TalendComponent] = []
        for index, node in enumerate(iter_by_local_name(root, "node"), start=1):
            component_name = first_attr(node, "componentName", "component-name") or "unknown"
            parameters = self._parse_parameters(node)
            unique_name = (
                parameters.get("UNIQUE_NAME")
                or first_attr(node, "name", "label")
                or f"{component_name}_{index}"
            )
            disabled = self._is_disabled(node, parameters)
            component = TalendComponent(
                id=first_attr(node, "id", "xmi:id"),
                name=unique_name,
                component_name=component_name,
                disabled=disabled,
                job=job_name,
                parameters=parameters,
            )
            components.append(component)
            if component_name.lower() in EXCLUDED_JOB_COMPONENTS_NORMALIZED:
                logger.info(
                    "[COUNT-DEBUG] Detected component: job=%s component=%s type=%s path=%s count_policy=included_in_component_count_not_a_job",
                    job_name,
                    component.name,
                    component.component_name,
                    item_file,
                )
            else:
                logger.info(
                    "[COUNT-DEBUG] Detected component: job=%s component=%s type=%s path=%s count_policy=included_in_component_count",
                    job_name,
                    component.name,
                    component.component_name,
                    item_file,
                )
        return components

    def _item_type(self, root: Element) -> str | None:
        if local_name(root.tag) == "ProcessType":
            return "ProcessItem"
        for element in root.iter():
            element_type = local_name(element.tag)
            if element_type.endswith("Item"):
                return element_type
        return None

    def _first_item_element(self, root: Element) -> Element | None:
        for element in root.iter():
            element_type = local_name(element.tag)
            if element_type.endswith("Item") and element_type != "ItemState":
                return element
        return None

    def _parse_contexts(self, root: Element) -> list[str]:
        contexts: set[str] = set()
        for context in iter_by_local_name(root, "context"):
            name = first_attr(context, "name", "context")
            if name:
                contexts.add(name)
        for parameter in iter_by_local_name(root, "contextParameter"):
            name = first_attr(parameter, "name")
            if name:
                contexts.add(name)
        return sorted(contexts)

    def _parse_context_groups(self, root: Element) -> list[ContextGroup]:
        groups: list[ContextGroup] = []
        for context in iter_by_local_name(root, "context"):
            name = first_attr(context, "name", "context") or "Default"
            file_path = first_attr(context, "filePath")
            params: list[ContextParameter] = []
            for param in iter_by_local_name(context, "contextParameter"):
                p_name = first_attr(param, "name") or ""
                p_value = first_attr(param, "value") or ""
                p_prompt = first_attr(param, "prompt")
                p_comment = first_attr(param, "comment")
                p_encrypted = first_attr(param, "encrypted") or "false"
                params.append(ContextParameter(
                    name=p_name, value=p_value,
                    prompt=p_prompt, comment=p_comment,
                    encrypted=p_encrypted.lower() in {"true", "1", "yes"},
                ))
            groups.append(ContextGroup(name=name, parameters=params, external_file_path=file_path))
        return groups

    def _parse_connections(self, root: Element) -> list[Connection]:
        connections: list[Connection] = []
        for conn in iter_by_local_name(root, "nodeConnection"):
            source = first_attr(conn, "source") or ""
            target = first_attr(conn, "target") or ""
            conn_type = first_attr(conn, "connectorType", "connectType") or "FLOW"
            label = first_attr(conn, "label")
            if source and target:
                connections.append(Connection(
                    source_id=source,
                    target_id=target,
                    connection_type=conn_type,
                    label=label,
                ))
        return connections

    def _parse_parameters(self, node: Element) -> dict[str, str]:
        parameters: dict[str, str] = {}
        for parameter in iter_by_local_name(node, "elementParameter"):
            name = first_attr(parameter, "name", "field")
            value = first_attr(parameter, "value")
            if name and value is not None:
                parameters[name] = value
        return parameters

    def _is_disabled(self, node: Element, parameters: dict[str, str]) -> bool:
        activation_value = (
            first_attr(node, "activated", "enabled")
            or parameters.get("ACTIVATE")
            or parameters.get("ENABLED")
        )
        return not bool_attr(activation_value, default=True)

    def _is_source_component(self, component_name: str) -> bool:
        normalized = component_name.lower()
        return any(hint in normalized for hint in SOURCE_HINTS)

    def _is_target_component(self, component_name: str) -> bool:
        normalized = component_name.lower()
        return any(hint in normalized for hint in TARGET_HINTS)

    def _detect_system(self, component_name: str) -> str | None:
        normalized = component_name.lower()
        for hint, label in SYSTEM_HINTS.items():
            if hint in normalized:
                return label
        return None

    def _first_element(self, root: Element, name: str) -> Element | None:
        for element in root.iter():
            if local_name(element.tag) == name:
                return element
        return None

    def _first_text(self, root: Element, *names: str) -> str | None:
        for element in root.iter():
            if local_name(element.tag) in names and element.text:
                return element.text.strip()
        return None
