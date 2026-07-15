from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.collection import Collection
from demisto_sdk.commands.validate.tools import (
    action_text_fragments,
    agent_text_fragments,
    estimate_tokens_for_texts,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class _Dep(NamedTuple):
    """A single agent dependency as returned by the structure query.

    ``name``/``description`` are graph node properties (sufficient to score
    skills and collections). ``path`` points at the dependency's source file so
    an action can be re-parsed from disk to recover its args/outputs schema,
    which is deliberately excluded from the graph and therefore unavailable on
    graph-property objects.
    """

    id: str
    name: Optional[str]
    description: Optional[str]
    path: Optional[str]
    type: Optional[str]


class _Deps(NamedTuple):
    """The direct dependencies of one agent, grouped for token estimation.

    - ``action_paths``: source-file paths of dependent actions; each is
      re-parsed from disk so its args/outputs (excluded from the graph) count
      toward the budget.
    - ``skill_summaries`` / ``collection_summaries``: ``(name, description)``
      pairs read straight from the graph, which is all a skill/collection
      contributes to the agent total.
    """

    action_paths: list[str]
    skill_summaries: list[tuple[Optional[str], Optional[str]]]
    collection_summaries: list[tuple[Optional[str], Optional[str]]]


ContentTypes = AgentixAgent | AgentixAction | AgentixSkill | Collection

AGENT_TOKEN_LIMIT = 50000

# One Cypher round trip resolves the whole structure GR116 needs:
#   step 1 - the affected agents: when $validate_all is true, every agent;
#            otherwise each agent that was modified itself, or that directly
#            uses a modified action/skill (both bound in $changed_ids).
#   step 2 - for every affected agent, all its direct action/skill/collection
#            dependencies, returned with the graph-node fields the token budget
#            needs (name + description) plus the source path (used to re-parse an
#            action's args/outputs, which are not stored in the graph).
# $validate_all (not the emptiness of $changed_ids) drives the validate-all-files
# fallback: in list/git mode $changed_ids can legitimately be empty and must then
# select NO agents rather than all of them.
_AGENT_DEPENDENCIES_QUERY = f"""
MATCH (a:{ContentType.AGENTIX_AGENT})
OPTIONAL MATCH (a)-[:{RelationshipType.USES}]->(changed)
WITH a,
     $validate_all
     OR (a.object_id IN $changed_ids)
     OR (changed IS NOT NULL AND changed.object_id IN $changed_ids) AS is_affected
WITH a WHERE is_affected
WITH DISTINCT a
OPTIONAL MATCH (a)-[:{RelationshipType.USES}]->(dep)
WHERE dep.content_type IN [
    '{ContentType.AGENTIX_ACTION}', '{ContentType.AGENTIX_SKILL}',
    '{ContentType.COLLECTION}'
]
RETURN a.object_id AS agent_id,
       collect(DISTINCT {{
           id: dep.object_id,
           name: dep.name,
           description: dep.description,
           path: dep.path,
           type: dep.content_type
       }}) AS deps
"""


class IsAgentTotalTokenBudgetValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR116"
    description = (
        "Checks that an AgentixAgent's total context - its name, description, and "
        "system instructions plus the name and description of every action, skill, "
        "and collection it depends on (and, for actions, their args/outputs "
        f"schema) - does not exceed {AGENT_TOKEN_LIMIT} estimated tokens."
    )
    rationale = (
        "At runtime the agent's own definition and the definitions of all its "
        "registered actions, skills, and collections are injected into the LLM "
        "context. If the combined size is too large it displaces task data in the "
        "context window and degrades the agent's performance."
    )
    error_message = (
        "The AgentixAgent '{0}' has a total estimated context of {1} tokens, which "
        f"exceeds the maximum allowed of {AGENT_TOKEN_LIMIT}. Reduce the agent's "
        "system instructions or the number/size of its actions, skills, and "
        "collections."
    )
    related_field = "systeminstructions"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self,
        content_items: Iterable[ContentTypes],
        validate_all_files: bool = False,
    ) -> list[ValidationResult]:
        logger.info(
            f"[{self.error_code}] START obtain_invalid_content_items_using_graph "
            f"(validate_all_files={validate_all_files})."
        )
        changed_ids = (
            []
            if validate_all_files
            else [content_item.object_id for content_item in content_items]
        )
        logger.info(
            f"[{self.error_code}] Computed changed_ids ({len(changed_ids)}): "
            f"{sorted(changed_ids)}."
        )

        if not validate_all_files and not changed_ids:
            logger.info(
                f"[{self.error_code}] No modified agents/actions/skills/collections - "
                "nothing to validate. Returning [] (no graph query issued)."
            )
            return []

        logger.info(
            f"[{self.error_code}] Resolving affected agents and their "
            f"dependencies via the single structure query "
            f"(validate_all={validate_all_files})."
        )
        agent_to_deps = self._affected_agents_with_dependencies(
            changed_ids, validate_all_files
        )
        if not agent_to_deps:
            logger.info(
                f"[{self.error_code}] No affected agents to validate "
                f"(validate_all_files={validate_all_files}, "
                f"changed_ids={sorted(changed_ids)}). Returning []."
            )
            return []

        logger.info(
            f"[{self.error_code}] Validating {len(agent_to_deps)} agent(s): "
            f"{sorted(agent_to_deps)}."
        )
        agents = self._fetch_agents(set(agent_to_deps))
        logger.info(
            f"[{self.error_code}] Fetched {len(agents)} agent object(s) from the "
            f"graph for {len(agent_to_deps)} affected agent id(s)."
        )

        results = [
            result
            for agent in agents
            if (result := self._validate_agent(agent, agent_to_deps))
        ]
        logger.info(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s) "
            f"out of {len(agents)} validated agent(s)."
        )
        return results

    def _validate_agent(
        self,
        agent: AgentixAgent,
        agent_to_deps: dict[str, _Deps],
    ) -> ValidationResult | None:
        """Estimate the agent's total token budget; flag it when over the limit."""
        deps = agent_to_deps.get(agent.object_id, _Deps([], [], []))
        total_tokens = estimate_tokens_for_texts(self._agent_fragments(agent, deps))
        logger.info(
            f"[{self.error_code}] Agent '{agent.display_name}' "
            f"(id='{agent.object_id}'): estimated {total_tokens} tokens across "
            f"{len(deps.action_paths)} action(s), {len(deps.skill_summaries)} "
            f"skill(s), and {len(deps.collection_summaries)} collection(s) "
            f"(limit {AGENT_TOKEN_LIMIT})."
        )
        if total_tokens <= AGENT_TOKEN_LIMIT:
            return None

        logger.info(
            f"[{self.error_code}] Agent '{agent.display_name}' EXCEEDS the "
            f"limit ({total_tokens} > {AGENT_TOKEN_LIMIT}) - flagging it."
        )
        return ValidationResult(
            validator=self,
            message=self.error_message.format(agent.display_name, total_tokens),
            content_object=agent,
        )

    @staticmethod
    def _agent_fragments(agent: AgentixAgent, deps: _Deps) -> List[Optional[str]]:
        """All token-bearing text fragments of the agent and its dependencies.

        The agent's own fields and each dependency's name/description come from
        the graph; each action is additionally re-parsed from its source path so
        its args/outputs schema (excluded from the graph) is included.
        """
        fragments: List[Optional[str]] = list(agent_text_fragments(agent))
        logger.info(
            f"[GR116] Building fragments for agent '{agent.object_id}': "
            f"{len(fragments)} own fragment(s), then {len(deps.action_paths)} "
            f"action path(s), {len(deps.skill_summaries)} skill summary(ies), "
            f"{len(deps.collection_summaries)} collection summary(ies)."
        )
        for action_path in deps.action_paths:
            action = IsAgentTotalTokenBudgetValidator._parse_action(action_path)
            if action is None:
                logger.info(
                    f"[GR116] Action path '{action_path}' did not parse into an "
                    "AgentixAction - contributing no tokens."
                )
                continue
            action_fragments = action_text_fragments(action)
            logger.info(
                f"[GR116] Re-parsed action '{action.object_id}' from "
                f"'{action_path}': +{len(action_fragments)} fragment(s) "
                "(incl. args/outputs)."
            )
            fragments.extend(action_fragments)
        for name, description in deps.skill_summaries:
            logger.info(f"[GR116] Adding skill summary (name='{name}') from the graph.")
            fragments.extend([name, description])
        for name, description in deps.collection_summaries:
            logger.info(
                f"[GR116] Adding collection summary (name='{name}') from the graph."
            )
            fragments.extend([name, description])
        logger.info(
            f"[GR116] Agent '{agent.object_id}' assembled {fragments} total "
            "text fragment(s) for token estimation."
        )
        return fragments

    @staticmethod
    def _parse_action(path: str) -> Optional[AgentixAction]:
        """Parse an AgentixAction from disk so its args/outputs are populated.

        The graph stores an action's scalar fields but excludes its args/outputs
        schema, so those must be recovered by re-parsing the source YAML. A path
        that cannot be parsed into an AgentixAction is skipped (it just does not
        contribute tokens) rather than failing the whole validation.
        """
        try:
            parsed = BaseContent.from_path(Path(path))
        except Exception:  # unreadable/invalid path -> contribute no tokens
            logger.debug(f"[GR116] Could not parse action from '{path}'.")
            return None
        return parsed if isinstance(parsed, AgentixAction) else None

    def _affected_agents_with_dependencies(
        self, changed_ids: list[str], validate_all: bool
    ) -> dict[str, _Deps]:
        """Return ``{agent_id: _Deps(...)}`` from a single structure query.

        Runs :data:`_AGENT_DEPENDENCIES_QUERY` (every agent when ``validate_all``,
        otherwise those modified themselves or owning a directly-modified
        dependency) and folds each agent's dependency rows into the grouped
        :class:`_Deps`: action source paths (re-parsed later for args/outputs) and
        skill/collection ``(name, description)`` summaries read straight from the
        graph.
        """
        logger.info(
            f"[GR116] Running structure query "
            f"(validate_all={validate_all}, changed_ids={sorted(changed_ids)})."
        )
        rows = self.graph.run_single_query(
            _AGENT_DEPENDENCIES_QUERY,
            changed_ids=changed_ids,
            validate_all=validate_all,
        )
        rows = rows or []
        logger.info(f"[GR116] Structure query returned {len(rows)} agent row(s).")
        agent_to_deps: dict[str, _Deps] = {}
        for row in rows:
            agent_id = row["agent_id"]
            deps = agent_to_deps.setdefault(agent_id, _Deps([], [], []))
            raw_deps = row.get("deps") or []
            logger.info(
                f"[GR116] Agent '{agent_id}': routing {len(raw_deps)} raw "
                "dependency row(s)."
            )
            for raw in raw_deps:
                self._route_dep(_Dep(**raw), deps)
            logger.info(
                f"[GR116] Agent '{agent_id}' grouped deps: "
                f"{len(deps.action_paths)} action(s), "
                f"{len(deps.skill_summaries)} skill(s), "
                f"{len(deps.collection_summaries)} collection(s)."
            )
        return agent_to_deps

    @staticmethod
    def _route_dep(dep: _Dep, deps: _Deps) -> None:
        """Add a single dependency row to the agent's grouped ``_Deps``."""
        # OPTIONAL MATCH yields a null dep for a dependency-less agent.
        if dep.id is None:
            logger.info("[GR116] Skipping null dependency row (agent has no deps).")
            return
        if dep.type == ContentType.AGENTIX_ACTION.value and dep.path:
            logger.info(
                f"[GR116] Routing action dep '{dep.id}' -> re-parse path "
                f"'{dep.path}'."
            )
            deps.action_paths.append(dep.path)
        elif dep.type == ContentType.AGENTIX_SKILL.value:
            logger.info(
                f"[GR116] Routing skill dep '{dep.id}' (name='{dep.name}') "
                "-> graph name+description."
            )
            deps.skill_summaries.append((dep.name, dep.description))
        elif dep.type == ContentType.COLLECTION.value:
            logger.info(
                f"[GR116] Routing collection dep '{dep.id}' (name='{dep.name}') "
                "-> graph name+description."
            )
            deps.collection_summaries.append((dep.name, dep.description))
        else:
            logger.info(
                f"[GR116] Ignoring dependency '{dep.id}' of unhandled type "
                f"'{dep.type}' (or action without a path)."
            )

    def _fetch_agents(self, agent_ids: set[str]) -> list[AgentixAgent]:
        """Fetch the affected AgentixAgent model objects by object_id."""
        return [
            node
            for node in self._search(ContentType.AGENTIX_AGENT, agent_ids)
            if isinstance(node, AgentixAgent)
        ]

    def _search(self, content_type: ContentType, object_ids: set[str]) -> list:
        """Fetch graph nodes of ``content_type`` for the given object ids."""
        if not object_ids:
            return []
        return self.graph.search(content_type=content_type, object_id=list(object_ids))
