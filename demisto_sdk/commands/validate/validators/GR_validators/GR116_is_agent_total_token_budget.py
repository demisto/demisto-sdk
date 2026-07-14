from __future__ import annotations

from abc import ABC
from typing import Dict, Iterable, List, Union

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.validate.tools import (
    estimate_agent_total_tokens,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

# GR116 must also run when an agent's dependency (an action or a skill) is
# modified, not only when the agent file itself changes. The framework's
# ``should_run`` gate keeps an item only if it is an instance of ``ContentTypes``
# (see base_validator.get_content_types), so the union below is what lets the
# modified actions/skills reach this validator (mirrors GR110's union).
ContentTypes = Union[AgentixAgent, AgentixAction, AgentixSkill]

AGENT_TOKEN_LIMIT = 50000


class IsAgentTotalTokenBudgetValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR116"
    description = (
        "Checks that an AgentixAgent's total context - its name, description, and "
        "system instructions plus the name and description of every action and skill "
        f"it depends on - does not exceed {AGENT_TOKEN_LIMIT} estimated tokens."
    )
    rationale = (
        "At runtime the agent's own definition and the definitions of all its "
        "registered actions and skills are injected into the LLM context. If the "
        "combined size is too large it displaces task data in the context window "
        "and degrades the agent's performance."
    )
    error_message = (
        "The AgentixAgent '{0}' has a total estimated context of {1} tokens, which "
        f"exceeds the maximum allowed of {AGENT_TOKEN_LIMIT}. Reduce the agent's "
        "system instructions or the number/size of its actions and skills."
    )
    related_field = "systeminstructions"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self,
        content_items: Iterable[ContentTypes],
        validate_all_files: bool = False,
    ) -> List[ValidationResult]:
        if validate_all_files:
            agents = [
                node
                for node in self.graph.search(content_type=ContentType.AGENTIX_AGENT)
                if isinstance(node, AgentixAgent)
            ]
        else:
            # In list/git mode a change can arrive either as the agent itself or
            # as one of its dependencies (an action or a skill). Collect every
            # affected agent, de-duplicated by ``object_id`` so that N modified
            # dependencies of the same agent still validate that agent only once
            # (see _collect_affected_agents).
            agents = list(self._collect_affected_agents(content_items).values())
        if not agents:
            return []

        logger.info(
            f"[{self.error_code}] Running on {len(agents)} AgentixAgent item(s): "
            f"{[agent.object_id for agent in agents]}."
        )
        results: List[ValidationResult] = []
        for agent in agents:
            dependent_actions, dependent_skills = self._resolve_dependencies(agent)
            total_tokens = estimate_agent_total_tokens(
                agent, dependent_actions, dependent_skills
            )
            logger.info(
                f"[{self.error_code}] Agent '{agent.display_name}' "
                f"(id='{agent.object_id}'): estimated {total_tokens} tokens across "
                f"{len(dependent_actions)} action(s) and {len(dependent_skills)} "
                f"skill(s) (limit {AGENT_TOKEN_LIMIT})."
            )
            if total_tokens > AGENT_TOKEN_LIMIT:
                logger.info(
                    f"[{self.error_code}] Agent '{agent.display_name}' EXCEEDS the "
                    f"limit ({total_tokens} > {AGENT_TOKEN_LIMIT}) - flagging it."
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            agent.display_name, total_tokens
                        ),
                        content_object=agent,
                    )
                )

        logger.info(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s)."
        )
        return results

    def _collect_affected_agents(
        self, content_items: Iterable[ContentTypes]
    ) -> Dict[str, AgentixAgent]:
        """Return the agents affected by ``content_items``, de-duplicated by id.

        An agent is "affected" when it is modified directly, or when one of its
        dependencies (an action or a skill) is modified. Because many
        dependencies can belong to the same agent, results are accumulated into a
        dict keyed by ``agent.object_id`` so each agent is validated exactly once
        (e.g. 8 modified actions of one agent yield a single agent entry, not 8).
        """
        agents_by_id: Dict[str, AgentixAgent] = {}
        for content_item in content_items:
            if isinstance(content_item, AgentixAgent):
                logger.info(
                    f"[{self.error_code}] Modified AgentixAgent "
                    f"'{content_item.object_id}' - will be validated directly."
                )
                agents_by_id[content_item.object_id] = content_item
            elif isinstance(content_item, AgentixAction):
                reached = self._agents_directly_using(
                    ContentType.AGENTIX_ACTION, content_item.object_id
                )
                logger.info(
                    f"[{self.error_code}] Modified AgentixAction "
                    f"'{content_item.object_id}' directly used by "
                    f"{len(reached)} agent(s): {[a.object_id for a in reached]}."
                )
                for agent in reached:
                    agents_by_id[agent.object_id] = agent
            elif isinstance(content_item, AgentixSkill):
                reached = self._agents_directly_using(
                    ContentType.AGENTIX_SKILL, content_item.object_id
                )
                logger.info(
                    f"[{self.error_code}] Modified AgentixSkill "
                    f"'{content_item.object_id}' directly used by "
                    f"{len(reached)} agent(s): {[a.object_id for a in reached]}."
                )
                for agent in reached:
                    agents_by_id[agent.object_id] = agent
        logger.info(
            f"[{self.error_code}] Collected {len(agents_by_id)} unique affected "
            f"agent(s) from the modified content items: {list(agents_by_id)}."
        )
        return agents_by_id

    def _agents_directly_using(
        self, content_type: ContentType, object_id: str
    ) -> List[AgentixAgent]:
        """Return the agents that DIRECTLY depend on the given action/skill.

        Only the direct edge ``agent -> action`` / ``agent -> skill`` is
        considered: an action reached only transitively (``agent -> skill ->
        action``) does NOT flag the agent here. The dependency is parsed from
        disk and has no relationships hydrated, so the node is re-fetched from
        the graph to read its incoming ``USES`` relationships (``used_by``),
        mirroring GR115's reverse-lookup pattern. Graph placeholders (e.g.
        ``UnknownContent``) lack ``used_by`` and are skipped. Agents are
        de-duplicated by ``object_id``.
        """
        agents: Dict[str, AgentixAgent] = {}
        for node in self.graph.search(content_type=content_type, object_id=object_id):
            used_by = getattr(node, "used_by", None)
            if not used_by:
                continue
            for relationship in used_by:
                target = relationship.content_item_to
                if isinstance(target, AgentixAgent):
                    agents[target.object_id] = target
        return list(agents.values())

    def _resolve_dependencies(
        self, agent: AgentixAgent
    ) -> tuple[List[AgentixAction], List[AgentixSkill]]:
        """Resolve the agent's dependent actions and skills from the content graph.

        Collects the ``AGENTIX_ACTION`` and ``AGENTIX_SKILL`` targets both from the
        agent's ``uses`` relationships and from any actions its registered skills
        depend on, then fetches the corresponding nodes from the graph so their
        name/description are available for token estimation.
        """
        action_ids = set(agent.actionids or [])
        skill_ids = set(agent.skillids or [])
        for relationship in agent.uses:
            node = relationship.content_item_to
            if node.content_type == ContentType.AGENTIX_ACTION:
                action_ids.add(node.object_id)
            elif node.content_type == ContentType.AGENTIX_SKILL:
                skill_ids.add(node.object_id)

        skills: List[AgentixSkill] = [
            node
            for node in self._search(ContentType.AGENTIX_SKILL, skill_ids)
            if isinstance(node, AgentixSkill)
        ]
        # A skill's action dependencies also count toward the agent's context.
        for skill in skills:
            for relationship in skill.uses:
                node = relationship.content_item_to
                if node.content_type == ContentType.AGENTIX_ACTION:
                    action_ids.add(node.object_id)

        actions: List[AgentixAction] = [
            node
            for node in self._search(ContentType.AGENTIX_ACTION, action_ids)
            if isinstance(node, AgentixAction)
        ]
        return actions, skills

    def _search(self, content_type: ContentType, object_ids: set) -> list:
        """Fetch graph nodes of ``content_type`` for the given object ids."""
        if not object_ids:
            return []
        search_kwargs: Dict = {
            "content_type": content_type,
            "object_id": list(object_ids),
        }
        return self.graph.search(**search_kwargs)
