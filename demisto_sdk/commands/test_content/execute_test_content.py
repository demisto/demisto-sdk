import os
import sys
from threading import Thread

import requests

from demisto_sdk.commands.test_content.ParallelLoggingManager import (
    ParallelLoggingManager,
)
from demisto_sdk.commands.test_content.TestContentClasses import (
    BuildContext,
)

SKIPPED_CONTENT_COMMENT = (
    "The following integrations/tests were collected by the CI build but are currently skipped. "
    "The collected tests are related to this pull request and might be critical."
)
COVERAGE_REPORT_COMMENT = "Link to the unit tests coverage report"


def _handle_github_response(response, logging_module) -> dict:
    res_dict = response.json()
    if not response.ok:
        logging_module.error(
            f'Add pull request comment failed: {res_dict.get("message")}',
            real_time=True,
        )
    return res_dict


def _add_pr_comment(comment, logging_module):
    token = os.environ["XSOAR_BOT_TEST_CONTENT"]
    branch_name = os.environ["CI_COMMIT_BRANCH"]
    sha1 = os.environ["CI_COMMIT_SHA"]

    query = f"?q={sha1}+repo:demisto/content+org:demisto+is:pr+is:open+head:{branch_name}+is:open"
    url = "https://api.github.com/search/issues"
    headers = {"Authorization": "Bearer " + token}

    is_skipped_tests_flow = "The following integrations/tests were collected" in comment

    try:
        response = requests.get(url + query, headers=headers, verify=False)
        res = _handle_github_response(response, logging_module)

        if res and res.get("total_count", 0) == 1:
            issue_url = (
                res["items"][0].get("comments_url") if res.get("items", []) else None
            )
            if issue_url:
                # Check if a comment about skipped tests already exists. If there is, first delete it and then post a
                # new comment:
                response = requests.get(issue_url, headers=headers, verify=False)
                issue_comments = _handle_github_response(response, logging_module)
                for existing_comment in issue_comments:
                    if (
                        is_skipped_tests_flow
                        and SKIPPED_CONTENT_COMMENT in existing_comment.get("body", "")
                    ) or (
                        not is_skipped_tests_flow
                        and COVERAGE_REPORT_COMMENT in existing_comment.get("body", "")
                    ):
                        comment_url = existing_comment.get("url")
                        requests.delete(comment_url, headers=headers, verify=False)
                response = requests.post(
                    issue_url, json={"body": comment}, headers=headers, verify=False
                )
                _handle_github_response(response, logging_module)
        else:
            logging_module.warning(
                "Add pull request comment failed: There is more then one open pull "
                f"request for branch {branch_name}.",
                real_time=True,
            )
    except Exception:
        logging_module.exception("Add pull request comment failed")


def execute_test_content(**kwargs):
    logging_manager = ParallelLoggingManager(
        "Run_Tests.log", real_time_logs_only=not kwargs["nightly"]
    )
    logging_manager.info(
        f'Starting to run tests on Server version:{kwargs["server_version"]} Server Type:{kwargs["server_type"]}'
    )
    build_context = BuildContext(kwargs, logging_manager)

    threads_list = []
    for index, server in enumerate(build_context.servers):
        thread_name = f"{server.machine}-{index} (execute_tests)"
        threads_list.append(Thread(target=server.execute_tests, name=thread_name))

    logging_manager.info("Finished creating configurations, starting to run tests.")
    for thread in threads_list:
        thread.start()

    for t in threads_list:
        t.join()

    logging_manager.info("Finished running tests.")
    for server in build_context.servers:
        if not server.tests_to_run.empty():
            logging_manager.critical(
                "Not all tests have been executed. Not destroying instances. Exiting",
                real_time=True,
            )
            sys.exit(1)
    if (
        build_context.tests_data_keeper.playbook_skipped_integration
        and build_context.build_name != "master"
        and not build_context.is_nightly
    ):
        skipped_integrations = "\n- ".join(
            build_context.tests_data_keeper.playbook_skipped_integration
        )
        comment = f"{SKIPPED_CONTENT_COMMENT}:\n- {skipped_integrations}"
        _add_pr_comment(comment, logging_manager)
    build_context.tests_data_keeper.print_test_summary(logging_manager)
    build_context.tests_data_keeper.create_result_files()

    if kwargs["nightly"]:
        build_number = kwargs["build_number"]
        build_context.tests_data_keeper.upload_playbook_result_json_to_bucket(
            kwargs["server_type"],
            f"playbook_report_{build_number}.xml",
            logging_manager,
        )
    if build_context.tests_data_keeper.failed_playbooks:
        logging_manager.critical(
            "Some tests have failed. Not destroying instances.", real_time=True
        )
        sys.exit(1)
