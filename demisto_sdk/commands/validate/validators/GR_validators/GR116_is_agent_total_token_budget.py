from __future__ import annotations

from abc import ABC
from typing import Dict, Iterable, List, Optional, Union

from packaging.version import InvalidVersion, Version

from demisto_sdk.commands.common.logger import logger
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

ContentTypes = Union[AgentixAgent, AgentixAction, AgentixSkill, Collection]

AGENT_CHAR_LIMIT = 200000


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
        changed_ids = (
            []
            if validate_all_files
            else [content_item.object_id for content_item in content_items]
        )

        if not validate_all_files and not changed_ids:
            return []

        affected_agents = self._affected_agents_with_dependencies(changed_ids)
        return [
            result
            for agent, dep_nodes in affected_agents
            if (result := self._validate_agent(agent, dep_nodes))
        ]

    def _validate_agent(
        self,
        agent: AgentixAgent,
        dep_nodes: Dict[str, dict],
    ) -> ValidationResult | None:
        """Count the agent's total char budget; flag it when over the limit."""
        fragments = self._agent_fragments(agent, dep_nodes)
        total_chars = count_chars_for_texts(fragments)
        logger.debug(
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
        own_fragments: List[Optional[str]] = [
            *agent_text_fragments(agent),
            *(agent.conversationstarters or []),
        ]
        logger.debug(
            f"[{self.error_code}] Agent '{agent.name}' (id='{agent.object_id}'): "
            f"own fields contribute {count_chars_for_texts(own_fragments)} char(s) "
            f"across {len(own_fragments)} fragment(s)."
        )

        fragments: List[Optional[str]] = list(own_fragments)
        for dep_id, node in dep_nodes.items():
            dep_fragments = dependency_text_fragments(node)
            logger.debug(
                f"[{self.error_code}] Agent '{agent.name}': dependency "
                f"id='{dep_id}' type='{node.get('content_type')}' "
                f"path='{node.get('path')}' fromversion='{node.get('fromversion')}' "
                f"contributes {count_chars_for_texts(dep_fragments)} char(s) "
                f"across {len(dep_fragments)} fragment(s)."
            )
            fragments.extend(dep_fragments)

        return fragments

    def _affected_agents_with_dependencies(
        self, changed_ids: list[str]
    ) -> list[tuple[AgentixAgent, Dict[str, dict]]]:
        """Return ``[(AgentixAgent, {dep_id: dep_node}), ...]`` from one query.

        Runs ``graph.get_agent_budget_dependencies`` (every agent when
        ``changed_ids`` is empty, otherwise those modified themselves or owning a
        directly-modified dependency). Each row carries the full agent node -
        reconstructed into an :class:`AgentixAgent` object so it can both score
        the agent's own fields and be attached to the ValidationResult without a
        second graph fetch - plus its dependency rows as full graph nodes,
        deduplicated by ``id`` to the highest-``fromversion`` node (mirroring what
        the platform loads at runtime when several files share the same id).
        """
        rows = self.graph.get_agent_budget_dependencies(changed_ids) or []
        scope = "all agents" if not changed_ids else f"{len(changed_ids)} changed id(s)"
        logger.debug(
            f"[{self.error_code}] Structure query ({scope}) returned "
            f"{len(rows)} agent row(s)."
        )

        affected: list[tuple[AgentixAgent, Dict[str, dict]]] = []
        for row in rows:
            # The interface reconstructs each row's agent node into a real
            # AgentixAgent (see neo4j_graph.get_agent_budget_dependencies).
            agent = row.get("agent")
            if agent is None:
                logger.debug(f"[{self.error_code}] Skipping a row with no agent node.")
                continue

            raw_deps = row.get("deps") or []
            dep_nodes: Dict[str, dict] = {}
            for raw in raw_deps:
                node = dict(raw)
                # Log every RAW dep (id + path) before dedup: two files for the
                # "same" action that re-parse to DIVERGENT object_ids (e.g.
                # CortexListIssues.yml -> 'SearchIssues') both survive the
                # id-based dedup and inflate the count. This line makes that gap
                # visible - a single logical action appearing under >1 id/path.
                logger.debug(
                    f"[{self.error_code}] Agent '{agent.name}': raw dep "
                    f"id='{node.get('object_id')}' "
                    f"type='{node.get('content_type')}' "
                    f"path='{node.get('path')}' "
                    f"fromversion='{node.get('fromversion')}'."
                )
                self._dedupe_dependency(node, dep_nodes)
            logger.debug(
                f"[{self.error_code}] Agent '{agent.name}' (id='{agent.object_id}'): "
                f"{len(raw_deps)} raw dep(s) deduped to {len(dep_nodes)} "
                f"(kept newest per id) -> ids={sorted(dep_nodes)}."
            )
            affected.append((agent, dep_nodes))
        return affected

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
