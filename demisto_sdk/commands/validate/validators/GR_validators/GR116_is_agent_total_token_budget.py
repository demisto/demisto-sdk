from __future__ import annotations

from abc import ABC
from typing import Dict, Iterable, List, Optional

from packaging.version import InvalidVersion, Version

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import versioned
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.objects.collection import Collection
from demisto_sdk.commands.validate.tools import (
    agent_text_fragments,
    count_chars_for_texts,
    dependency_text_fragments,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAgent | AgentixAction | AgentixSkill | Collection

AGENT_CHAR_LIMIT = 200000

# Only agents available from this platform version onward are budget-checked;
# earlier agents predate the char-budget contract this validator enforces.
MIN_AGENT_FROMVERSION = "8.15.0"

# One Cypher round trip resolves the whole structure GR116 needs:
#   step 1 - the affected agents: when $validate_all is true, every agent;
#            otherwise each agent that was modified itself, or that directly
#            uses a modified action/skill (both bound in $changed_ids).
#   step 2 - for every affected agent, the full agent node (so it is
#            reconstructed into an AgentixAgent object - the same object other
#            graph validators attach to their ValidationResult - carrying the
#            agent's own char-bearing fields: name, description, system
#            instructions, conversation starters) plus all its direct action/
#            skill/collection dependencies, each returned as its full graph node.
#            Each dependency node is then reconstructed into its real object and
#            scored by the shared fragment collectors (an action is re-parsed
#            from its path so its args/outputs, excluded from the graph, count).
# Returning the full agent and dependency nodes here means GR116 never has to
# issue a second graph query to fetch those objects.
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
RETURN a AS agent, collect(DISTINCT dep) AS deps
"""


class IsAgentTotalTokenBudgetValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR116"
    description = (
        "Checks that an AgentixAgent's total context - its name, description, "
        "system instructions, and conversation starters plus the name and "
        "description of every action, skill, and collection it depends on (and, "
        "for actions, their args/outputs schema) - does not exceed "
        f"{AGENT_CHAR_LIMIT} characters."
    )
    rationale = (
        "At runtime the agent's own definition and the definitions of all its "
        "registered actions, skills, and collections are injected into the LLM "
        "context. If the combined size is too large it displaces task data in the "
        "context window and degrades the agent's performance. The budget is in "
        "characters (~4 chars = 1 token) as a proxy for token cost."
    )
    error_message = (
        "The AgentixAgent '{0}' has a total context of {1} characters, which "
        f"exceeds the maximum allowed of {AGENT_CHAR_LIMIT}. Reduce the agent's "
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
        content_items = list(content_items)
        # TEMP[GR116-debug]: entry state - mode + the exact content items received.
        logger.opt(colors=False).debug(
            f"[GR116][debug] obtain_invalid_content_items_using_graph called: "
            f"validate_all_files={validate_all_files}, "
            f"received {len(content_items)} content item(s): "
            f"{[getattr(ci, 'object_id', '<no-object_id>') for ci in content_items]}"
        )
        changed_ids = (
            []
            if validate_all_files
            else [content_item.object_id for content_item in content_items]
        )
        # TEMP[GR116-debug]: the computed changed_ids the query will be run with.
        logger.opt(colors=False).debug(
            f"[GR116][debug] computed changed_ids ({len(changed_ids)}): {changed_ids}"
        )

        if not validate_all_files and not changed_ids:
            logger.opt(colors=False).debug(
                "[GR116][debug] early-return: not validate_all_files and empty "
                "changed_ids -> no agents to check."
            )
            return []

        affected_agents = self._affected_agents_with_dependencies(
            changed_ids, validate_all_files
        )
        # TEMP[GR116-debug]: how many agents the query selected, and which.
        logger.opt(colors=False).debug(
            f"[GR116][debug] _affected_agents_with_dependencies returned "
            f"{len(affected_agents)} agent(s): "
            f"{[a.object_id for a, _ in affected_agents]}"
        )
        results = [
            result
            for agent, dep_nodes in affected_agents
            if (result := self._validate_agent(agent, dep_nodes))
        ]
        # TEMP[GR116-debug]: how many agents ended up flagged over budget.
        logger.opt(colors=False).debug(
            f"[GR116][debug] finished: {len(results)} agent(s) exceeded the budget "
            f"out of {len(affected_agents)} checked."
        )
        return results

    def _validate_agent(
        self,
        agent: AgentixAgent,
        dep_nodes: Dict[str, dict],
    ) -> ValidationResult | None:
        """Count the agent's total char budget; flag it when over the limit."""
        fragments = self._agent_fragments(agent, dep_nodes)
        total_chars = count_chars_for_texts(fragments)
        # One summary line per agent. colors=False: the agent name is free-form
        # content that may contain angle brackets, which loguru would otherwise
        # parse as color tags.
        logger.opt(colors=False).info(
            f"[{self.error_code}] Agent '{agent.name}' (id='{agent.object_id}'): "
            f"checked {len(dep_nodes)} dependency(ies) -> "
            f"{len(fragments)} fragment(s), {total_chars} char(s) "
            f"(limit {AGENT_CHAR_LIMIT})."
        )
        if total_chars <= AGENT_CHAR_LIMIT:
            return None

        return ValidationResult(
            validator=self,
            message=self.error_message.format(agent.name, total_chars),
            content_object=agent,
        )

    def _agent_fragments(
        self, agent: AgentixAgent, dep_nodes: Dict[str, dict]
    ) -> List[Optional[str]]:
        """All char-bearing text fragments of the agent and its dependencies.

        The agent's own fields (name, description, system instructions, and
        conversation starters) come from the graph node. Every deduplicated
        dependency node is then routed through :func:`dependency_text_fragments`,
        which reconstructs the real object and scores it with the shared fragment
        collectors (an action is re-parsed from its path so its args/outputs,
        excluded from the graph, count).
        """
        fragments: List[Optional[str]] = [
            *agent_text_fragments(agent),
            *(agent.conversationstarters or []),
        ]
        # TEMP: per-item char breakdown so a verbose validate run prints exactly
        # how many chars each agent field / dependency contributes.
        logger.opt(colors=False).debug(
            f"[GR116][breakdown] agent '{agent.name}': own fields = "
            f"{count_chars_for_texts(fragments)} char(s) "
            f"(name+description+systeminstructions+{len(agent.conversationstarters or [])} "
            f"conversationstarters)."
        )
        for dep_id, node in dep_nodes.items():
            dep_fragments = dependency_text_fragments(node)
            logger.opt(colors=False).debug(
                f"[GR116][breakdown] dependency '{dep_id}' "
                f"(type='{node.get('content_type')}', "
                f"fromversion='{node.get('fromversion')}'): "
                f"{count_chars_for_texts(dep_fragments)} char(s), "
                f"{len(dep_fragments)} fragment(s)."
            )
            fragments.extend(dep_fragments)

        return fragments

    def _affected_agents_with_dependencies(
        self, changed_ids: list[str], validate_all: bool
    ) -> list[tuple[AgentixAgent, Dict[str, dict]]]:
        """Return ``[(AgentixAgent, {dep_id: dep_node}), ...]`` from one query.

        Runs :data:`_AGENT_DEPENDENCIES_QUERY` (every agent when ``validate_all``,
        otherwise those modified themselves or owning a directly-modified
        dependency). Each row carries the full agent node - reconstructed into an
        :class:`AgentixAgent` object so it can both score the agent's own fields
        and be attached to the ValidationResult without a second graph fetch -
        plus its dependency rows as full graph nodes, deduplicated by ``id`` to
        the highest-``fromversion`` node (mirroring what the platform loads at
        runtime when several files share the same id).
        """
        # TEMP[GR116-debug]: log the exact query params before running it.
        logger.opt(colors=False).debug(
            f"[GR116][debug] running _AGENT_DEPENDENCIES_QUERY with "
            f"validate_all={validate_all}, changed_ids={changed_ids}"
        )
        rows = (
            self.graph.run_single_query(
                _AGENT_DEPENDENCIES_QUERY,
                changed_ids=changed_ids,
                validate_all=validate_all,
            )
            or []
        )
        # rows = list(rows)
        # TEMP[GR116-debug]: raw number of rows the query returned (one per agent).
        logger.opt(colors=False).debug(
            f"[GR116][debug] query returned {len(rows)} raw row(s)."
        )

        affected: list[tuple[AgentixAgent, Dict[str, dict]]] = []
        for index, row in enumerate(rows):
            raw_agent = row.get("agent")
            # TEMP[GR116-debug]: identify each raw agent node before parsing.
            raw_agent_id = dict(raw_agent).get("object_id") if raw_agent else None
            raw_deps = row.get("deps") or []
            logger.opt(colors=False).debug(
                f"[GR116][debug] row #{index}: raw agent id="
                f"{raw_agent_id!r}, raw dep count={len(raw_deps)}."
            )
            agent = self._parse_agent(raw_agent)
            if agent is None:
                # TEMP[GR116-debug]: a row was dropped because its agent node
                # could not be reconstructed - this hides an agent from results.
                logger.opt(colors=False).debug(
                    f"[GR116][debug] row #{index}: agent id={raw_agent_id!r} "
                    f"could NOT be parsed -> row skipped."
                )
                continue

            dep_nodes: Dict[str, dict] = {}
            for raw in raw_deps:
                self._dedupe_dependency(dict(raw), dep_nodes)
            # TEMP[GR116-debug]: post-dedup dependency ids for this agent.
            logger.opt(colors=False).debug(
                f"[GR116][debug] row #{index}: parsed agent "
                f"'{agent.object_id}', {len(dep_nodes)} deduped dependency(ies): "
                f"{list(dep_nodes.keys())}"
            )
            affected.append((agent, dep_nodes))
        return affected

    @staticmethod
    def _parse_agent(node: Optional[dict]) -> Optional[AgentixAgent]:
        """Reconstruct an AgentixAgent object from its graph node properties.

        The structure query returns the full agent node, so the same object type
        other graph validators attach to their results is available here without
        any additional graph query.
        """
        if not node:
            # TEMP[GR116-debug]: a null/empty agent node reached the parser.
            logger.opt(colors=False).debug(
                "[GR116][debug] _parse_agent received an empty/None node."
            )
            return None
        try:
            return AgentixAgent.parse_obj(dict(node))
        except Exception as exc:  # malformed node -> cannot validate/flag this agent
            # TEMP[GR116-debug]: log the concrete parse error + offending id.
            node_id = dict(node).get("object_id")
            logger.opt(colors=False).debug(
                f"[GR116][debug] _parse_agent FAILED for agent id={node_id!r}: "
                f"{type(exc).__name__}: {exc}"
            )
            return None

    @staticmethod
    def _dedupe_dependency(node: dict, dep_nodes: Dict[str, dict]) -> None:
        """Keep, per dependency ``id``, only the highest-``fromversion`` node.

        When several files expose the same id (version variants, or the same id
        living in both a vendor pack and a standalone ``AgentixAction_*``/vendor
        pack), only the newest is counted, matching what the platform loads at
        runtime.
        """
        dep_id = node.get("object_id")
        # OPTIONAL MATCH yields a null dep for a dependency-less agent.
        if dep_id is None:
            return
        existing = dep_nodes.get(dep_id)
        if existing is None or _is_newer(
            node.get("fromversion"), existing.get("fromversion")
        ):
            dep_nodes[dep_id] = node


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
