import os
import sys
from threading import Thread

import requests
from demisto_sdk.commands.test_content.ParallelLoggingManager import \
    ParallelLoggingManager
from demisto_sdk.commands.test_content.TestContentClasses import (
    BuildContext, ServerContext)


def _handle_github_response(response, logging_module) -> dict:
    res_dict = response.json()
    if not response.ok:
        logging_module.error(f'Add pull request comment failed: {res_dict.get("message")}', real_time=True)
    return res_dict


def _add_pr_comment(comment, logging_module):
    token = os.environ['CONTENT_GITHUB_TOKEN']
    branch_name = os.environ['CIRCLE_BRANCH']
    sha1 = os.environ['CIRCLE_SHA1']

    query = '?q={}+repo:demisto/content+org:demisto+is:pr+is:open+head:{}+is:open'.format(sha1, branch_name)
    url = 'https://api.github.com/search/issues'
    headers = {'Authorization': 'Bearer ' + token}
    try:
        response = requests.get(url + query, headers=headers, verify=False)
        res = _handle_github_response(response, logging_module)

        if res and res.get('total_count', 0) == 1:
            issue_url = res['items'][0].get('comments_url') if res.get('items', []) else None
            if issue_url:
                response = requests.post(issue_url, json={'body': comment}, headers=headers, verify=False)
                _handle_github_response(response, logging_module)
        else:
            logging_module.warning('Add pull request comment failed: There is more then one open pull '
                                   f'request for branch {branch_name}.', real_time=True)
    except Exception:
        logging_module.exception('Add pull request comment failed')


def execute_test_content(**kwargs):
    logging_manager = ParallelLoggingManager('Run_Tests.log', real_time_logs_only=not kwargs['nightly'])
    build_context = BuildContext(kwargs, logging_manager)
    threads_list = []
    for server_ip in build_context.instances_ips:
        tests_execution_instance = ServerContext(build_context, server_ip)
        threads_list.append(Thread(target=tests_execution_instance.execute_tests))

    for thread in threads_list:
        thread.start()

    for t in threads_list:
        t.join()

    if not build_context.unmockable_tests_to_run.empty() or not build_context.mockable_tests_to_run.empty():
        raise Exception('Not all tests have been executed')
    if build_context.tests_data_keeper.playbook_skipped_integration and build_context.build_name != 'master':
        comment = 'The following integrations are skipped and critical for the test:\n {}'. \
            format('\n- '.join(build_context.tests_data_keeper.playbook_skipped_integration))
        _add_pr_comment(comment, logging_manager)
    build_context.tests_data_keeper.print_test_summary(build_context.isAMI, logging_manager)
    build_context.tests_data_keeper.create_result_files()
    if build_context.tests_data_keeper.failed_playbooks:
        logging_manager.critical("Some tests have failed. Not destroying instances.", real_time=True)
        sys.exit(1)
