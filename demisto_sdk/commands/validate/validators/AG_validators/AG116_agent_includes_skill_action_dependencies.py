from __future__ import annotations

from abc import ABC
from typing import Dict, Iterable, List, Optional

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAgent


class IsAgentIncludesSkillActionDependenciesValidator(BaseValidator[ContentTypes], ABC):
    error_code = "AG116"
    description = (
        "Validates that an AgentixAgent which registers an AgentixSkill also "
        "registers every AgentixAction that the skill depends on."
    )
    rationale = (
        "An AgentixSkill references actions (via '<action=action-id>' tokens in its "
        "body), which become the skill's action dependencies in the content graph. "
        "When an agent registers a skill, the agent must also include all of that "
        "skill's action dependencies in its own action list ('actionids'); otherwise "
        "the skill will reference actions the agent cannot run."
    )
    error_message = (
        "The AgentixAgent '{0}' registers the skill '{1}' but is missing the "
        "following action dependency(ies) required by that skill: {2}. Add the "
        "missing action(s) to the agent's 'actionids'."
    )
    related_field = "actionids"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self,
        content_items: Iterable[ContentTypes],
        validate_all_files: bool = False,
    ) -> List[ValidationResult]:
        if validate_all_files:
            # Validate every agent in the repository.
            agents = [
                node
                for node in self.graph.search(content_type=ContentType.AGENTIX_AGENT)
                if isinstance(node, AgentixAgent)
            ]
        else:
            agents = [
                content_item
                for content_item in content_items
                if isinstance(content_item, AgentixAgent)
            ]
        if not agents:
            return []

        required_skill_ids = (
            None
            if validate_all_files
            else {skill_id for agent in agents for skill_id in agent.skillids or []}
        )
        if required_skill_ids is not None and not required_skill_ids:
            return []
        skill_to_action_ids = self._build_skill_to_action_ids_map(required_skill_ids)

        results: List[ValidationResult] = []
        for agent in agents:
            agent_action_ids = self._agent_action_ids(agent)

            for skill_id in agent.skillids or []:
                required_action_ids = skill_to_action_ids.get(skill_id)
                if not required_action_ids:
                    continue

                missing = [
                    action_id
                    for action_id in required_action_ids
                    if action_id not in agent_action_ids
                ]
                if not missing:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            agent.display_name,
                            skill_id,
                            ", ".join(
                                f"'{action_id}'" for action_id in sorted(set(missing))
                            ),
                        ),
                        content_object=agent,
                    )
                )

        return results

    def _build_skill_to_action_ids_map(
        self, skill_ids: Optional[set] = None
    ) -> Dict[str, List[str]]:
        """Maps each skill's ``object_id`` to the action ids it depends on.

        Fetches ``AGENTIX_SKILL`` nodes from the graph (which includes their
        relationships) and collects each skill's ``AGENTIX_ACTION`` ``uses`` targets.
        When ``skill_ids`` is provided, only those skills are fetched instead of
        every skill in the repository.
        """
        skill_to_action_ids: Dict[str, List[str]] = {}
        search_kwargs: Dict = {"content_type": ContentType.AGENTIX_SKILL}
        if skill_ids is not None:
            search_kwargs["object_id"] = list(skill_ids)
        skills = self.graph.search(**search_kwargs)
        for skill in skills:
            if not isinstance(skill, AgentixSkill):
                continue
            skill_to_action_ids[skill.object_id] = [
                relationship.content_item_to.object_id
                for relationship in skill.uses
                if relationship.content_item_to.content_type
                == ContentType.AGENTIX_ACTION
            ]
        return skill_to_action_ids

    @staticmethod
    def _agent_action_ids(agent: AgentixAgent) -> set:
        """Collects the action ids the agent registers.

        Uses both the agent's declared ``actionids`` field and any
        ``AGENTIX_ACTION`` targets resolved through the content graph.
        """
        action_ids = set(agent.actionids or [])
        for relationship in agent.uses:
            node = relationship.content_item_to
            if node.content_type == ContentType.AGENTIX_ACTION:
                action_ids.add(node.object_id)
        return action_ids
