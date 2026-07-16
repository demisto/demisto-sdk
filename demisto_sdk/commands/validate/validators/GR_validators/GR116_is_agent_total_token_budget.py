from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from packaging.version import InvalidVersion, Version

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import versioned
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.collection import Collection
from demisto_sdk.commands.validate.tools import (
    action_text_fragments,
    estimate_tokens_for_texts,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class _Dependency(NamedTuple):
    """A single agent dependency as returned by the structure query.

    ``name``/``description`` are graph node properties (sufficient to score
    skills and collections). ``path`` points at the dependency's source file so
    an action can be re-parsed from disk to recover its args/outputs schema,
    which is deliberately excluded from the graph and therefore unavailable on
    graph-property objects. ``fromversion`` is used to pick a single winner when
    several files expose the same action ``id`` (e.g. version variants like
    ``SearchCases`` and ``SearchCases_8_15``): only the highest ``fromversion``
    is counted, mirroring what the platform loads at runtime.
    """

    id: str
    name: Optional[str]
    description: Optional[str]
    path: Optional[str]
    type: Optional[str]
    fromversion: Optional[str]


class _GroupedDependencies(NamedTuple):
    """The direct dependencies of one agent, grouped for token estimation.

    - ``action_paths``: source-file path per dependent action, keyed by action
      ``id`` and deduplicated to the highest-``fromversion`` file so a single
      logical action is counted once even when several version-variant files
      share its ``id``. Each surviving path is re-parsed from disk so its
      args/outputs (excluded from the graph) count toward the budget.
    - ``skill_summaries`` / ``collection_summaries``: ``(name, description)``
      pairs read straight from the graph, which is all a skill/collection
      contributes to the agent total.
    """

    action_paths: Dict[str, Tuple[str, Optional[str]]]
    skill_summaries: list[tuple[Optional[str], Optional[str]]]
    collection_summaries: list[tuple[Optional[str], Optional[str]]]


ContentTypes = AgentixAgent | AgentixAction | AgentixSkill | Collection

# AGENT_TOKEN_LIMIT = 50000
AGENT_TOKEN_LIMIT = 23000  ### for demo only

# Only agents available from this platform version onward are budget-checked;
# earlier agents predate the token-budget contract this validator enforces.
MIN_AGENT_FROMVERSION = "8.15.0"

# One Cypher round trip resolves the whole structure GR116 needs:
#   step 1 - the affected agents: when $validate_all is true, every agent;
#            otherwise each agent that was modified itself, or that directly
#            uses a modified action/skill (both bound in $changed_ids).
#   step 2 - for every affected agent, the full agent node (so it is
#            reconstructed into an AgentixAgent object - the same object other
#            graph validators attach to their ValidationResult - carrying the
#            agent's own token-bearing fields: name, description, system
#            instructions, conversation starters) plus all its direct action/
#            skill/collection dependencies, returned with the graph-node fields
#            the token budget needs (name + description) plus the source path
#            (used to re-parse an action's args/outputs, which are not stored in
#            the graph).
# Returning the full agent node here means GR116 never has to issue a second
# graph query to fetch the agent objects.
# $validate_all (not the emptiness of $changed_ids) drives the validate-all-files
# fallback: in list/git mode $changed_ids can legitimately be empty and must then
# select NO agents rather than all of them.
_AGENT_DEPENDENCIES_QUERY = f"""
MATCH (a:{ContentType.AGENTIX_AGENT})
WHERE {versioned("a.fromversion")} >= {versioned(MIN_AGENT_FROMVERSION)}
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
RETURN a AS agent,
    collect(DISTINCT {{
        id: dep.object_id,
        name: dep.name,
        description: dep.description,
        path: dep.path,
        type: dep.content_type,
        fromversion: dep.fromversion
    }}) AS deps
"""


class IsAgentTotalTokenBudgetValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR116"
    description = (
        "Checks that an AgentixAgent's total context - its name, description, "
        "system instructions, and conversation starters plus the name and "
        "description of every action, skill, and collection it depends on (and, "
        "for actions, their args/outputs schema) - does not exceed "
        f"{AGENT_TOKEN_LIMIT} estimated tokens."
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
        changed_ids = (
            []
            if validate_all_files
            else [content_item.object_id for content_item in content_items]
        )

        if not validate_all_files and not changed_ids:
            return []

        affected_agents = self._affected_agents_with_dependencies(
            changed_ids, validate_all_files
        )
        return [
            result
            for agent, deps in affected_agents
            if (result := self._validate_agent(agent, deps))
        ]

    def _validate_agent(
        self,
        agent: AgentixAgent,
        deps: _GroupedDependencies,
    ) -> ValidationResult | None:
        """Estimate the agent's total token budget; flag it when over the limit."""
        fragments = self._agent_fragments(agent, deps)
        total_tokens = estimate_tokens_for_texts(fragments)
        # One summary line per agent. colors=False: the agent name is free-form
        # content that may contain angle brackets, which loguru would otherwise
        # parse as color tags.
        logger.opt(colors=False).info(
            f"[{self.error_code}] Agent '{agent.name}' (id='{agent.object_id}'): "
            f"checked {len(deps.action_paths)} action(s), "
            f"{len(deps.skill_summaries)} skill(s), "
            f"{len(deps.collection_summaries)} collection(s) -> "
            f"{len(fragments)} fragment(s), {total_tokens} token(s) "
            f"(limit {AGENT_TOKEN_LIMIT})."
        )
        if total_tokens <= AGENT_TOKEN_LIMIT:
            return None

        return ValidationResult(
            validator=self,
            message=self.error_message.format(agent.name, total_tokens),
            content_object=agent,
        )

    def _agent_fragments(
        self, agent: AgentixAgent, deps: _GroupedDependencies
    ) -> List[Optional[str]]:
        """All token-bearing text fragments of the agent and its dependencies.

        The agent's own fields (name, description, system instructions, and
        conversation starters) and each dependency's name/description come from
        the graph. Each action is additionally re-parsed from its source path so
        its args/outputs schema (excluded from the graph) is included; a path
        that does not parse into an AgentixAction contributes nothing.
        """
        fragments: List[Optional[str]] = [
            agent.name,
            agent.description,
            agent.systeminstructions,
            *(agent.conversationstarters or []),
        ]
        # TEMP: per-item token breakdown so a verbose validate run prints exactly
        # how many tokens each agent field / action / skill contributes.
        logger.opt(colors=False).debug(
            f"[GR116][breakdown] agent '{agent.name}': own fields = "
            f"{estimate_tokens_for_texts(fragments)} token(s) "
            f"(name+description+systeminstructions+{len(agent.conversationstarters or [])} "
            f"conversationstarters)."
        )
        for path, fromversion in deps.action_paths.values():
            action = self._parse_action_from_path(path)
            if action is None:
                logger.opt(colors=False).debug(
                    f"[GR116][breakdown] action path '{path}': UNPARSEABLE -> 0 tokens."
                )
                continue
            action_fragments = action_text_fragments(action)
            logger.opt(colors=False).debug(
                f"[GR116][breakdown] action '{action.object_id}' "
                f"(path='{path}', fromversion='{fromversion}'): "
                f"{estimate_tokens_for_texts(action_fragments)} "
                f"token(s), {len(action_fragments)} fragment(s)."
            )
            fragments.extend(action_fragments)

        for name, description in deps.skill_summaries:
            logger.opt(colors=False).debug(
                f"[GR116][breakdown] skill '{name}': "
                f"{estimate_tokens_for_texts([name, description])} token(s) "
                f"(name+description only)."
            )
            fragments.extend([name, description])
        for name, description in deps.collection_summaries:
            logger.opt(colors=False).debug(
                f"[GR116][breakdown] collection '{name}': "
                f"{estimate_tokens_for_texts([name, description])} token(s)."
            )
            fragments.extend([name, description])

        return fragments

    @staticmethod
    def _parse_action_from_path(path: str) -> Optional[AgentixAction]:
        """Parse an AgentixAction from disk so its args/outputs are populated.

        The graph stores an action's scalar fields but excludes its args/outputs
        schema, so those must be recovered by re-parsing the source YAML. A path
        that cannot be parsed into an AgentixAction returns ``None`` (it just does
        not contribute tokens) rather than failing the whole validation.
        """
        try:
            parsed = BaseContent.from_path(Path(path))
        except Exception:  # unreadable/invalid path -> contribute no tokens
            logger.debug(f"[GR116] Could not parse action from '{path}'.")
            return None
        return parsed if isinstance(parsed, AgentixAction) else None

    def _affected_agents_with_dependencies(
        self, changed_ids: list[str], validate_all: bool
    ) -> list[tuple[AgentixAgent, _GroupedDependencies]]:
        """Return ``[(AgentixAgent, _GroupedDependencies), ...]`` from one query.

        Runs :data:`_AGENT_DEPENDENCIES_QUERY` (every agent when ``validate_all``,
        otherwise those modified themselves or owning a directly-modified
        dependency). Each row carries the full agent node - reconstructed into an
        :class:`AgentixAgent` object so it can both score the agent's own fields
        and be attached to the ValidationResult without a second graph fetch -
        plus its dependency rows, which are grouped into a
        :class:`_GroupedDependencies`: action source paths (re-parsed later for
        args/outputs) and skill/collection ``(name, description)`` summaries read
        straight from the graph.
        """
        rows = (
            self.graph.run_single_query(
                _AGENT_DEPENDENCIES_QUERY,
                changed_ids=changed_ids,
                validate_all=validate_all,
            )
            or []
        )

        affected: list[tuple[AgentixAgent, _GroupedDependencies]] = []
        for row in rows:
            agent = self._parse_agent(row.get("agent"))
            if agent is None:
                continue

            deps = _GroupedDependencies({}, [], [])
            for raw in row.get("deps") or []:
                self._route_dependency(_Dependency(**raw), deps)
            affected.append((agent, deps))
        return affected

    @staticmethod
    def _parse_agent(node: Optional[dict]) -> Optional[AgentixAgent]:
        """Reconstruct an AgentixAgent object from its graph node properties.

        The structure query returns the full agent node, so the same object type
        other graph validators attach to their results is available here without
        any additional graph query.
        """
        if not node:
            return None
        try:
            return AgentixAgent.parse_obj(dict(node))
        except Exception:  # malformed node -> cannot validate/flag this agent
            logger.debug("[GR116] Could not parse an agent node into an AgentixAgent.")
            return None

    @staticmethod
    def _route_dependency(dep: _Dependency, deps: _GroupedDependencies) -> None:
        """Add a single dependency row to the agent's grouped dependencies.

        Actions are keyed by ``id`` and deduplicated to the highest
        ``fromversion``: when several files expose the same action id (version
        variants, or the same id living in both a vendor pack and a standalone
        ``AgentixAction_*`` pack), only the newest is counted, matching what the
        platform loads at runtime.
        """
        # OPTIONAL MATCH yields a null dep for a dependency-less agent.
        if dep.id is None:
            return
        if dep.type == ContentType.AGENTIX_ACTION.value and dep.path:
            existing = deps.action_paths.get(dep.id)
            if existing is None or _is_newer(dep.fromversion, existing[1]):
                deps.action_paths[dep.id] = (dep.path, dep.fromversion)
        elif dep.type == ContentType.AGENTIX_SKILL.value:
            deps.skill_summaries.append((dep.name, dep.description))
        elif dep.type == ContentType.COLLECTION.value:
            deps.collection_summaries.append((dep.name, dep.description))
        else:
            logger.opt(colors=False).debug(
                f"[GR116] Ignoring dependency '{dep.id}' of unhandled type "
                f"'{dep.type}' (or action without a path)."
            )


def _is_newer(candidate: Optional[str], current: Optional[str]) -> bool:
    """Return True when ``candidate`` is a strictly higher version than ``current``.

    Used to pick the highest-``fromversion`` file among duplicate action ids. An
    unparseable/missing version sorts lowest, so a valid version always wins over
    a missing one, and a missing one never displaces an existing pick.
    """

    def _parse(value: Optional[str]) -> Version:
        try:
            return Version(value) if value else Version("0")
        except InvalidVersion:
            return Version("0")

    return _parse(candidate) > _parse(current)
