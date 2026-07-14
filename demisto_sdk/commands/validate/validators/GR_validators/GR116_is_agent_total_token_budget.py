from __future__ import annotations

from abc import ABC
from typing import Iterable, NamedTuple

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.validate.tools import estimate_agent_total_tokens
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class _DepIds(NamedTuple):
    """The direct action/skill dependency ids of a single agent."""

    actions: set[str]
    skills: set[str]


# The union lets modified actions/skills (not just agents) reach this validator:
# should_run keeps an item only if it is an instance of ContentTypes, and GR116
# must also run when an agent's dependency changes (mirrors GR110's union).
ContentTypes = AgentixAgent | AgentixAction | AgentixSkill

AGENT_TOKEN_LIMIT = 50000

# One Cypher round trip resolves the whole structure GR116 needs:
#   step 1 - the affected agents: when $validate_all is true, every agent;
#            otherwise each agent that was modified itself, or that directly
#            uses a modified action/skill (both bound in $changed_ids).
#   step 2 - for every affected agent, all its direct action/skill dependencies.
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
    '{ContentType.AGENTIX_ACTION}', '{ContentType.AGENTIX_SKILL}'
]
RETURN a.object_id AS agent_id,
       collect(DISTINCT {{id: dep.object_id, type: dep.content_type}}) AS deps
"""


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
    ) -> list[ValidationResult]:
        changed_ids = self._changed_agentix_ids(content_items)
        if not validate_all_files and not changed_ids:
            logger.info(
                f"[{self.error_code}] No modified agents/actions/skills - "
                "nothing to validate."
            )
            return []

        agent_to_deps = self._affected_agents_with_dependencies(
            changed_ids, validate_all_files
        )
        if not agent_to_deps:
            logger.info(
                f"[{self.error_code}] No affected agents to validate "
                f"(validate_all_files={validate_all_files}, "
                f"changed_ids={sorted(changed_ids)})."
            )
            return []

        logger.info(
            f"[{self.error_code}] Validating {len(agent_to_deps)} agent(s): "
            f"{sorted(agent_to_deps)}."
        )
        agents, actions_by_id, skills_by_id = self._hydrate(agent_to_deps)

        results = [
            result
            for agent in agents
            if (
                result := self._validate_agent(
                    agent, agent_to_deps, actions_by_id, skills_by_id
                )
            )
        ]
        logger.info(
            f"[{self.error_code}] Finished. Found {len(results)} invalid item(s)."
        )
        return results

    @staticmethod
    def _changed_agentix_ids(content_items: Iterable[ContentTypes]) -> set[str]:
        """The object_ids of the modified AgentixAgent/Action/Skill items."""
        return {
            content_item.object_id
            for content_item in content_items
            if isinstance(content_item, (AgentixAgent, AgentixAction, AgentixSkill))
        }

    def _validate_agent(
        self,
        agent: AgentixAgent,
        agent_to_deps: dict[str, _DepIds],
        actions_by_id: dict[str, AgentixAction],
        skills_by_id: dict[str, AgentixSkill],
    ) -> ValidationResult | None:
        """Estimate the agent's total token budget; flag it when over the limit."""
        deps = agent_to_deps.get(agent.object_id, _DepIds(set(), set()))
        dependent_actions = [
            actions_by_id[i] for i in deps.actions if i in actions_by_id
        ]
        dependent_skills = [skills_by_id[i] for i in deps.skills if i in skills_by_id]
        total_tokens = estimate_agent_total_tokens(
            agent, dependent_actions, dependent_skills
        )
        logger.info(
            f"[{self.error_code}] Agent '{agent.display_name}' "
            f"(id='{agent.object_id}'): estimated {total_tokens} tokens across "
            f"{len(dependent_actions)} action(s) and {len(dependent_skills)} "
            f"skill(s) (limit {AGENT_TOKEN_LIMIT})."
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

    def _affected_agents_with_dependencies(
        self, changed_ids: set[str], validate_all: bool
    ) -> dict[str, _DepIds]:
        """Return ``{agent_id: _DepIds(actions, skills)}`` in one graph query.

        Runs :data:`_AGENT_DEPENDENCIES_QUERY` (every agent when ``validate_all``,
        otherwise those modified themselves or owning a directly-modified
        dependency) and folds the result into a per-agent dependency table.
        """
        rows = self.graph.run_single_query(
            _AGENT_DEPENDENCIES_QUERY,
            changed_ids=list(changed_ids),
            validate_all=validate_all,
        )
        agent_to_deps: dict[str, _DepIds] = {}
        for row in rows or []:
            deps = agent_to_deps.setdefault(row["agent_id"], _DepIds(set(), set()))
            for dep in row.get("deps") or []:
                # OPTIONAL MATCH yields a null dep for a dependency-less agent.
                if dep.get("id") is None:
                    continue
                if dep["type"] == ContentType.AGENTIX_ACTION.value:
                    deps.actions.add(dep["id"])
                elif dep["type"] == ContentType.AGENTIX_SKILL.value:
                    deps.skills.add(dep["id"])
        return agent_to_deps

    def _hydrate(
        self, agent_to_deps: dict[str, _DepIds]
    ) -> tuple[
        list[AgentixAgent],
        dict[str, AgentixAction],
        dict[str, AgentixSkill],
    ]:
        """Batch-fetch the model objects needed for token estimation.

        The graph nodes only store scalar properties, but the token budget also
        depends on each action's args/outputs schema and each skill's/agent's
        related-file bodies, which live on the parsed model objects. Fetch the
        agents and the union of their dependency ids in one read per type.
        """
        action_ids = set().union(*(d.actions for d in agent_to_deps.values()), set())
        skill_ids = set().union(*(d.skills for d in agent_to_deps.values()), set())

        agents = [
            node
            for node in self._search(ContentType.AGENTIX_AGENT, set(agent_to_deps))
            if isinstance(node, AgentixAgent)
        ]
        actions_by_id = {
            node.object_id: node
            for node in self._search(ContentType.AGENTIX_ACTION, action_ids)
            if isinstance(node, AgentixAction)
        }
        skills_by_id = {
            node.object_id: node
            for node in self._search(ContentType.AGENTIX_SKILL, skill_ids)
            if isinstance(node, AgentixSkill)
        }
        return agents, actions_by_id, skills_by_id

    def _search(self, content_type: ContentType, object_ids: set[str]) -> list:
        """Fetch graph nodes of ``content_type`` for the given object ids."""
        if not object_ids:
            return []
        return self.graph.search(content_type=content_type, object_id=list(object_ids))
