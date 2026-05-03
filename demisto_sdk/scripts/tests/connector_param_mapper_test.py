import json
import logging
from pathlib import Path

import pytest
import yaml

from demisto_sdk.scripts.connector_param_mapper import (
    decide_capabilities,
    map_params_to_capabilities,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_yml(
    name: str = "MyIntegration",
    configuration: list | None = None,
    script: dict | None = None,
) -> dict:
    return {
        "name": name,
        "configuration": configuration or [],
        "script": script or {"commands": []},
    }


# ---------------------------------------------------------------------------
# Step 1 - capability decision tests
# ---------------------------------------------------------------------------
class TestDecideCapabilities:
    def test_only_general_configurations(self):
        yml = _build_yml()
        assert decide_capabilities(yml) == {"general_configurations": []}

    def test_fetch_secrets_added(self):
        yml = _build_yml(
            configuration=[{"name": "isFetchCredentials", "type": 8}],
        )
        result = decide_capabilities(yml)
        assert "Fetch Secrets" in result
        assert "Automation" not in result

    def test_log_collection_normal(self):
        # isfetchevents true but name has no eventcollector and no get-events cmd
        yml = _build_yml(
            name="SomeSiem",
            script={
                "isfetchevents": True,
                "commands": [
                    {"name": "siem-get-alert"},
                    {"name": "siem-list-cases"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Log Collection" in result
        assert "Automation" in result  # has non-excluded commands

    def test_log_collection_early_exit_eventcollector_name(self):
        yml = _build_yml(
            name="MyEventCollector",
            script={
                "isfetchevents": True,
                "commands": [{"name": "do-something"}],
            },
        )
        result = decide_capabilities(yml)
        assert result == {"general_configurations": [], "Log Collection": []}

    def test_log_collection_early_exit_single_get_events_command(self):
        yml = _build_yml(
            name="SomeIntegration",
            script={
                "isfetchevents": True,
                "commands": [
                    {"name": "vendor-get-events"},
                    {"name": "vendor-list"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert result == {"general_configurations": [], "Log Collection": []}

    def test_log_collection_no_early_exit_with_two_get_events(self):
        # 2 commands matching "get-events" should NOT trigger early exit
        yml = _build_yml(
            name="SomeIntegration",
            script={
                "isfetchevents": True,
                "commands": [
                    {"name": "vendor-get-events"},
                    {"name": "vendor-other-get-events"},
                    {"name": "vendor-list"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Log Collection" in result
        assert "Automation" in result

    def test_fetch_issues_added(self):
        yml = _build_yml(script={"isfetch": True, "commands": []})
        result = decide_capabilities(yml)
        assert "Fetch Issues" in result

    def test_fetch_issues_skipped_when_platform_false(self):
        yml = _build_yml(
            script={"isfetch": True, "isfetch:platform": False, "commands": []}
        )
        result = decide_capabilities(yml)
        assert "Fetch Issues" not in result

    def test_threat_intel_added(self):
        yml = _build_yml(
            name="GenericTI",
            script={
                "feed": True,
                "commands": [
                    {"name": "ti-get-something"},
                    {"name": "ti-list"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Threat Intelligence & Enrichment" in result
        assert "Automation" in result

    def test_threat_intel_early_exit_feed_in_name(self):
        yml = _build_yml(
            name="MyFeedSource",
            script={"feed": True, "commands": [{"name": "ti-action"}]},
        )
        result = decide_capabilities(yml)
        assert result == {
            "general_configurations": [],
            "Threat Intelligence & Enrichment": [],
        }

    def test_threat_intel_early_exit_single_get_indicators(self):
        yml = _build_yml(
            name="SomeTI",
            script={
                "feed": True,
                "commands": [
                    {"name": "vendor-get-indicators"},
                    {"name": "vendor-other"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert result == {
            "general_configurations": [],
            "Threat Intelligence & Enrichment": [],
        }

    def test_fetch_assets_added(self):
        yml = _build_yml(script={"isfetchassets": True, "commands": []})
        result = decide_capabilities(yml)
        assert "Fetch Assets and Vulnerabilities" in result

    def test_automation_added(self):
        yml = _build_yml(
            script={
                "commands": [
                    {"name": "vendor-do-stuff"},
                    {"name": "vendor-fetch-events"},
                ]
            }
        )
        result = decide_capabilities(yml)
        assert "Automation" in result

    def test_automation_not_added_when_only_excluded_commands(self):
        yml = _build_yml(
            script={
                "commands": [
                    {"name": "vendor-get-events"},
                    {"name": "vendor-get-indicators"},
                    {"name": "fetch-incidents"},
                    {"name": "fetch-events"},
                    {"name": "fetch-credentials"},
                ]
            }
        )
        result = decide_capabilities(yml)
        assert "Automation" not in result

    def test_combined_capabilities(self):
        yml = _build_yml(
            name="BigIntegration",
            configuration=[{"name": "isFetchCredentials"}],
            script={
                "isfetch": True,
                "isfetchassets": True,
                "commands": [
                    {"name": "big-do-stuff"},
                    {"name": "big-list"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Fetch Secrets" in result
        assert "Fetch Issues" in result
        assert "Fetch Assets and Vulnerabilities" in result
        assert "Automation" in result

    # ------------------------------------------------------------------
    # Rule 2 early-exit precondition tests (Option B fix)
    # ------------------------------------------------------------------
    def test_event_collector_with_isfetchassets_keeps_both_capabilities(self):
        """Multi-purpose collector: isfetchevents + isfetchassets + name contains
        'eventcollector' must NOT short-circuit; both capabilities must remain."""
        yml = _build_yml(
            name="JamfProtectEventCollector",
            script={
                "isfetchevents": True,
                "isfetchassets": True,
                "commands": [
                    {"name": "jamf-protect-get-events"},
                    {"name": "jamf-protect-get-computer-assets"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Log Collection" in result
        assert "Fetch Assets and Vulnerabilities" in result

    def test_event_collector_with_isfetch_keeps_both_capabilities(self):
        """Multi-purpose collector: isfetchevents + isfetch + name contains
        'eventcollector' must NOT short-circuit; both capabilities must remain."""
        yml = _build_yml(
            name="MyEventCollector",
            script={
                "isfetchevents": True,
                "isfetch": True,
                "commands": [
                    {"name": "vendor-get-events"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Log Collection" in result
        assert "Fetch Issues" in result

    def test_event_collector_with_feed_keeps_both_capabilities(self):
        """Multi-purpose collector: isfetchevents + feed + name contains
        'eventcollector' must NOT short-circuit; both capabilities must remain.

        Note: the command list intentionally avoids triggering Rule 4's own
        early-exit (no single 'get-indicators' command) so we can verify
        that BOTH Log Collection and Threat Intelligence & Enrichment remain.
        """
        yml = _build_yml(
            name="MyEventCollector",
            script={
                "isfetchevents": True,
                "feed": True,
                "commands": [
                    {"name": "vendor-get-events"},
                    {"name": "vendor-action"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Log Collection" in result
        assert "Threat Intelligence & Enrichment" in result

    def test_pure_event_collector_still_short_circuits(self):
        """Regression guard: when isfetchevents is the only fetch flag and the
        name contains 'eventcollector', the early-exit must still fire."""
        yml = _build_yml(
            name="MyEventCollector",
            script={
                "isfetchevents": True,
                "commands": [
                    {"name": "do-something"},
                    {"name": "vendor-get-events"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert result == {"general_configurations": [], "Log Collection": []}

    def test_event_collector_with_fetch_credentials_param_keeps_both(self):
        """Multi-purpose collector: isfetchevents + isFetchCredentials param +
        name contains 'eventcollector' must NOT short-circuit."""
        yml = _build_yml(
            name="MyEventCollector",
            configuration=[{"name": "isFetchCredentials", "type": 8}],
            script={
                "isfetchevents": True,
                "commands": [
                    {"name": "vendor-get-events"},
                ],
            },
        )
        result = decide_capabilities(yml)
        assert "Log Collection" in result
        assert "Fetch Secrets" in result


# ---------------------------------------------------------------------------
# Step 2 - param mapping tests
# ---------------------------------------------------------------------------
class TestMapParamsToCapabilities:
    def test_test_module_param_without_default_goes_to_general(self):
        capabilities = {"general_configurations": [], "Automation": []}
        command_params = {
            "integration": "X",
            "commands": {"test-module": ["url", "api_key"]},
        }
        param_defaults = {"api_key": "secret"}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert "url" in result["general_configurations"]
        assert "api_key" not in result["general_configurations"]

    def test_test_module_param_with_default_skipped(self):
        capabilities = {"general_configurations": [], "Automation": []}
        command_params = {
            "integration": "X",
            "commands": {"test-module": ["api_key"]},
        }
        param_defaults = {"api_key": "secret"}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert "api_key" not in result["general_configurations"]

    def test_single_capability_shortcut(self):
        # only 2 keys → all unique command params go into the non-general one
        capabilities = {"general_configurations": [], "Log Collection": []}
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "fetch-events": ["max_fetch", "first_fetch"],
                "vendor-get-events": ["query"],
            },
        }
        param_defaults = {"max_fetch": 30, "first_fetch": "3 days", "query": ""}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert result["general_configurations"] == ["url"]
        # all unique params (excluding the one already in general_configurations)
        assert sorted(result["Log Collection"]) == sorted(
            ["max_fetch", "first_fetch", "query"]
        )

    def test_multi_capability_fetch_incidents_to_fetch_issues(self):
        capabilities = {
            "general_configurations": [],
            "Fetch Issues": [],
            "Automation": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": [],
                "fetch-incidents": ["incident_query", "max_incidents"],
                "vendor-do-stuff": ["arg1"],
            },
        }
        param_defaults = {
            "incident_query": "",
            "max_incidents": 50,
            "arg1": "x",
        }
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert sorted(result["Fetch Issues"]) == sorted(
            ["incident_query", "max_incidents"]
        )
        assert result["Automation"] == ["arg1"]

    def test_multi_capability_other_command_to_automation(self):
        capabilities = {
            "general_configurations": [],
            "Fetch Issues": [],
            "Automation": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "vendor-action-1": ["a"],
                "vendor-action-2": ["b"],
            },
        }
        param_defaults = {"a": 1, "b": 2}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert sorted(result["Automation"]) == ["a", "b"]
        assert result["Fetch Issues"] == []

    def test_multi_capability_missing_target_logs_warning(self, caplog):
        # Fetch Issues capability is NOT present, but fetch-incidents command provides params
        capabilities = {
            "general_configurations": [],
            "Automation": [],
            "Log Collection": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "fetch-incidents": ["missing_param"],
                "vendor-action": ["a"],
            },
        }
        param_defaults = {"missing_param": 1, "a": 2}
        with caplog.at_level(logging.WARNING):
            result = map_params_to_capabilities(
                capabilities, command_params, param_defaults
            )
        # The param should not be placed anywhere
        assert "missing_param" not in result["Automation"]
        assert "missing_param" not in result["general_configurations"]
        # And a warning should have been logged
        all_messages = " ".join(r.getMessage() for r in caplog.records)
        assert "missing_param" in all_messages
        assert "Fetch Issues" in all_messages

    def test_get_events_command_routes_to_log_collection(self):
        """Substring routing: a command containing 'get-events' should be routed
        to 'Log Collection' instead of the default 'Automation' fallback,
        provided 'Log Collection' exists in the capabilities."""
        capabilities = {
            "general_configurations": [],
            "Log Collection": [],
            "Automation": [],
        }
        command_params = {
            "integration": "MyProduct",
            "commands": {
                "myproduct-get-events": ["events_param"],
                "myproduct-do-action": ["action_param"],
            },
        }
        param_defaults = {"events_param": 1, "action_param": 2}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert result["Log Collection"] == ["events_param"]
        assert result["Automation"] == ["action_param"]

    def test_get_events_command_falls_back_to_automation_without_log_collection(
        self,
    ):
        """If 'Log Collection' is NOT in capabilities, a 'get-events' command
        should fall back to 'Automation' (no special routing)."""
        capabilities = {
            "general_configurations": [],
            "Automation": [],
        }
        command_params = {
            "integration": "MyProduct",
            "commands": {
                "myproduct-get-events": ["events_param"],
            },
        }
        param_defaults = {"events_param": 1}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        # With only 2 capabilities, Step 2.2 shortcut places everything in
        # the non-general capability (Automation).
        assert result["Automation"] == ["events_param"]

    def test_get_indicators_command_routes_to_threat_intel(self):
        """Substring routing: a command containing 'get-indicators' should be
        routed to 'Threat Intelligence & Enrichment' instead of the default
        'Automation' fallback, provided that capability exists."""
        capabilities = {
            "general_configurations": [],
            "Threat Intelligence & Enrichment": [],
            "Automation": [],
        }
        command_params = {
            "integration": "MyFeed",
            "commands": {
                "myfeed-get-indicators": ["indicators_param"],
                "myfeed-do-action": ["action_param"],
            },
        }
        param_defaults = {"indicators_param": 1, "action_param": 2}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert result["Threat Intelligence & Enrichment"] == ["indicators_param"]
        assert result["Automation"] == ["action_param"]

    def test_get_indicators_command_falls_back_to_automation_without_threat_intel(
        self,
    ):
        """If 'Threat Intelligence & Enrichment' is NOT in capabilities, a
        'get-indicators' command should fall back to 'Automation'."""
        capabilities = {
            "general_configurations": [],
            "Fetch Issues": [],
            "Automation": [],
        }
        command_params = {
            "integration": "MyProduct",
            "commands": {
                "myproduct-get-indicators": ["indicators_param"],
            },
        }
        param_defaults = {"indicators_param": 1}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert result["Automation"] == ["indicators_param"]
        assert result["Fetch Issues"] == []

    def test_dedup_param_in_multiple_capabilities_moves_to_general(self):
        capabilities = {
            "general_configurations": [],
            "Fetch Issues": [],
            "Automation": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "fetch-incidents": ["shared"],
                "vendor-action": ["shared", "unique"],
            },
        }
        param_defaults = {"shared": 1, "unique": 2}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert "shared" in result["general_configurations"]
        assert "shared" not in result["Fetch Issues"]
        assert "shared" not in result["Automation"]
        assert "unique" in result["Automation"]

    def test_dedup_param_in_general_and_capability_keeps_general(self):
        # If a param is in general_configurations AND in another capability,
        # _deduplicate should remove it from the capability and keep it in general.
        capabilities = {
            "general_configurations": [],
            "Fetch Issues": [],
            "Automation": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "fetch-incidents": ["url"],
            },
        }
        param_defaults = {}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert result["general_configurations"].count("url") == 1
        assert "url" not in result["Fetch Issues"]

    def test_orphan_params_logged(self, caplog):
        capabilities = {"general_configurations": [], "Automation": []}
        command_params = {
            "integration": "X",
            "commands": {"vendor-action": ["a"]},
        }
        # 'orphan_param' is in defaults but never appears in any command
        param_defaults = {"a": 1, "orphan_param": "ghost"}
        with caplog.at_level(logging.WARNING):
            map_params_to_capabilities(capabilities, command_params, param_defaults)
        all_messages = " ".join(r.getMessage() for r in caplog.records)
        assert "orphan_param" in all_messages


# ---------------------------------------------------------------------------
# Step 2.1.5 - manual command-to-capability mapping tests
# ---------------------------------------------------------------------------
class TestManualMapping:
    def test_manual_mapping_empty_dict_preserves_existing_behavior(self):
        """An empty manual mapping must produce identical results to omitting
        the parameter entirely."""
        capabilities = {
            "general_configurations": [],
            "Fetch Issues": [],
            "Automation": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "fetch-incidents": ["incident_query", "max_incidents"],
                "vendor-do-stuff": ["arg1"],
            },
        }
        param_defaults = {
            "incident_query": "",
            "max_incidents": 50,
            "arg1": "x",
        }
        baseline = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        with_empty_manual = map_params_to_capabilities(
            capabilities,
            command_params,
            param_defaults,
            manual_command_to_capability={},
        )
        assert baseline == with_empty_manual

    def test_manual_mapping_routes_long_running_to_custom_capability(self):
        """Primary use case: route long-running-execution to a brand-new
        'Connection Health' capability that is not in the initial mapping."""
        capabilities = {"general_configurations": [], "Automation": []}
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "long-running-execution": ["url", "port"],
                "my-cmd": ["url", "filter"],
            },
        }
        param_defaults = {"url": None, "port": "8080", "filter": ""}
        manual = {"long-running-execution": ["Connection Health"]}
        result = map_params_to_capabilities(
            capabilities,
            command_params,
            param_defaults,
            manual_command_to_capability=manual,
        )
        assert "Connection Health" in result
        assert "port" in result["Connection Health"]
        assert "filter" in result["Automation"]
        # 'url' appears in test-module + long-running + my-cmd → dedup → general
        assert "url" in result["general_configurations"]
        assert "url" not in result["Connection Health"]
        assert "url" not in result["Automation"]

    def test_manual_mapping_overrides_command_to_capability_constant(self):
        """Manual mapping must take precedence over COMMAND_TO_CAPABILITY
        (e.g. fetch-events would automatically route to 'Log Collection')."""
        capabilities = {
            "general_configurations": [],
            "Log Collection": [],
            "Automation": [],
        }
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "fetch-events": ["url", "lookback"],
                "my-cmd": ["url"],
            },
        }
        param_defaults = {"url": None, "lookback": "1h"}
        manual = {"fetch-events": ["Custom Cap"]}
        result = map_params_to_capabilities(
            capabilities,
            command_params,
            param_defaults,
            manual_command_to_capability=manual,
        )
        assert "Custom Cap" in result
        assert "lookback" in result["Custom Cap"]
        assert "lookback" not in result["Log Collection"]

    def test_manual_mapping_multi_target_routes_to_all_listed(self):
        """Manual mapping with multiple target capabilities routes the params
        into every listed capability; dedup later moves shared params into
        general_configurations."""
        capabilities = {"general_configurations": [], "Automation": []}
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "my-cmd": ["url", "shared", "extra"],
            },
        }
        param_defaults = {"url": None, "shared": "x", "extra": "y"}
        manual = {"my-cmd": ["Cap A", "Cap B"]}
        result = map_params_to_capabilities(
            capabilities,
            command_params,
            param_defaults,
            manual_command_to_capability=manual,
        )
        assert "Cap A" in result
        assert "Cap B" in result
        # 'shared' and 'extra' were placed in BOTH Cap A and Cap B → dedup
        # moves them into general_configurations and clears them from the caps.
        assert "shared" in result["general_configurations"]
        assert "extra" in result["general_configurations"]
        assert result["Cap A"] == []
        assert result["Cap B"] == []

    def test_manual_mapping_with_existing_capability_no_duplicate_keys(self):
        """When the manual target capability already exists, do not create a
        duplicate key, and ensure the command is not double-routed via Step 2.3."""
        capabilities = {"general_configurations": [], "Automation": []}
        command_params = {
            "integration": "X",
            "commands": {
                "test-module": ["url"],
                "my-cmd": ["url", "filter"],
            },
        }
        param_defaults = {"url": None, "filter": ""}
        manual = {"my-cmd": ["Automation"]}
        result = map_params_to_capabilities(
            capabilities,
            command_params,
            param_defaults,
            manual_command_to_capability=manual,
        )
        # 'Automation' key exists exactly once, with 'filter' present once.
        assert list(result.keys()).count("Automation") == 1
        assert result["Automation"].count("filter") == 1
        assert "filter" in result["Automation"]


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------
class TestEndToEnd:
    def test_e2e_simple_integration(self, tmp_path: Path):
        # Build a small fake integration YML
        yml_content = {
            "name": "TinyIntegration",
            "configuration": [{"name": "url", "type": 0}],
            "script": {
                "isfetch": True,
                "commands": [
                    {"name": "fetch-incidents"},
                    {"name": "tiny-do-stuff"},
                ],
            },
        }
        yml_path = tmp_path / "tiny.yml"
        yml_path.write_text(yaml.safe_dump(yml_content))

        capabilities = decide_capabilities(yml_content)
        assert "Fetch Issues" in capabilities
        assert "Automation" in capabilities

        command_params = {
            "integration": "TinyIntegration",
            "commands": {
                "test-module": ["url"],
                "fetch-incidents": ["max_fetch"],
                "tiny-do-stuff": ["arg1"],
            },
        }
        param_defaults = {"max_fetch": 50, "arg1": "x"}
        result = map_params_to_capabilities(
            capabilities, command_params, param_defaults
        )
        assert result == {
            "general_configurations": ["url"],
            "Fetch Issues": ["max_fetch"],
            "Automation": ["arg1"],
        }

        # Write out and reload to make sure JSON serialisation works.
        out = tmp_path / "out.json"
        out.write_text(json.dumps(result, indent=2))
        loaded = json.loads(out.read_text())
        assert loaded == result

    def test_e2e_exabeam_yml(self):
        yml_path = Path(
            "/Users/yhayun/dev/demisto/content/Packs/"
            "ExabeamSecurityOperationsPlatform/Integrations/"
            "ExabeamSecOpsPlatform/ExabeamSecOpsPlatform.yml"
        )
        if not yml_path.exists():
            pytest.skip(f"Exabeam YML not found at {yml_path}")
        with open(yml_path) as f:
            integration_yml = yaml.safe_load(f)

        result = decide_capabilities(integration_yml)
        # ExabeamSecOpsPlatform: isfetchevents=True AND isfetch=True (with
        # isfetch:platform=False so Fetch Issues itself is skipped). Because
        # other fetch flags are present, Rule 2's early-exit must NOT fire —
        # Log Collection remains and Automation is added for non-excluded
        # commands like "exabeam-platform-event-search".
        assert "Log Collection" in result
        assert "Automation" in result
        assert "Fetch Issues" not in result  # isfetch:platform=False blocks it
        assert result["general_configurations"] == []
