import ast
import os

import klara
from klara.contract import solver
from klara.contract.solver import TestCase, MANAGER, nodes
import ast as ast_mod
import astor
from demisto_sdk.commands.common.tools import get_json
import logging

loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
print(loggers)
COMMENT = "\n\tWhen:\n\tGiven:\n\tThen:\n\t"
DIRECTORY_PATH = None
COMMANDS = None
MODULE_NAME = None
VERBOSE = False

# ----------------- Monkey Patching----------------------------------------

class TestCase:
    def __init__(self, func, module, id=0):
        self.asserts = []
        self.func = func
        self.id = id
        self.module = module
        self.request_mocks = []
        self.inputs = []
        self.client_name = None
        self.command_call = None

    def to_ast(self):
        body = [ast_mod.Expr(value=ast_mod.Constant(value=COMMENT))]
        body.extend(self.inputs)
        body.extend(self.request_mocks)
        body.append(self.command_call)
        body.extend(self.asserts)
        request_mocker = ast_name('requests_mock')

        test_func = ast_mod.FunctionDef(
            name=f"test_{self.func.name}",
            args=ast_mod.arguments(
                posonlyargs=[], args=[self.client_name, request_mocker], vararg=None, kwonlyargs=[], kw_defaults=[],
                kwarg=None, defaults=[]
            ),
            body=body,
            decorator_list=[],
            returns=None
        )
        return test_func


class TestModule:
    def __init__(self, module):
        self.functions = []
        self.imports = [ast_mod.Import(names=[ast_mod.alias(name='pytest')]),
                        ast_mod.Import(names=[ast_mod.alias(name='io')]),
                        ast_mod.ImportFrom(module='CommonServerPython', names=[ast_mod.alias(name='*')], level=0)]
        self.module = module
        self.server_url = ast_mod.Assign(targets=[ast_name('SERVER_URL')],
                                         value=ast_mod.Constant(value='https://test_url.com'))

    def to_ast(self):
        body = []
        body.extend(self.imports)
        body.append(self.server_url)
        body.extend([util_json_builder(), generate_test_client()])
        body.extend([f.to_ast() for f in self.functions if f.asserts])
        return ast_mod.Module(body=body)


def solve_function(self, func: nodes.FunctionDef, client_ast) -> TestCase:
    with MANAGER.initialize_z3_var_from_func(func):
        self.context.no_cache = True
        self.pre_conditions(func)
        test_case = TestCase(func, self.id)

        # Get local client instance name
        client_class_name = client_ast.name
        client_name = get_client_name(func, client_class_name)

        # Compose mock args as inputs to the function
        args_dict = get_mocked_args(func.name)
        args_list, client_calls = instance_dict_parser(func.instance_dict, client_name)
        args = args_builder(args_list, args_dict)

        # Compose request_mock calls for each API call made
        request_mocks = request_mock_ast_builder(client_ast, client_calls)

        # Compose a call to the command
        command_call_ast = call_command_ast_builder(func.name, args)

        # Compose command results assertions
        assertions_command = []
        returned_value = get_return_values(func)
        if returned_value:
            assertions_command = create_command_results_assertions(returned_value.keywords, func.name)

        # Compose test case object
        test_case.client_name = client_name
        test_case.inputs = args
        test_case.request_mocks = request_mocks
        test_case.command_call = command_call_ast
        test_case.asserts = assertions_command

        self.id += 1
        self.context.no_cache = False
        return test_case


def solve(self) -> TestModule:
    test_module = TestModule(self.file_name)
    self.visit(self.as_tree)
    client_ast = get_client_ast(self.as_tree)
    names_to_import = [client_ast.name]
    for func in self.functions:
        if not str(func.name).endswith("_command") or not generate_unit_test_decision_maker(str(func.name)):
            continue
        if VERBOSE:
            print(f"Analyzing function: {func} at line: {getattr(func, 'lineno', -1)}")
        try:
            ast_func = self.solve_function(func, client_ast)
            test_module.functions.append(ast_func)
            names_to_import.append(func.name)
        except ValueError:
            if VERBOSE:
                print(f"Skipped function: {func} due to one of its argument doesn't have type")
        MANAGER.clear_z3_cache()
    test_module.imports.append(build_imports(MODULE_NAME, names_to_import))
    return test_module


solver.ContractSolver.solve_function = solve_function
solver.ContractSolver.solve = solve
solver.TestCase = TestCase
solver.TestModule = TestModule


# ----------------- Custom ast nodes builder-------------------------------

def ast_name(id, ctx=ast_mod.Load()):
    """
    Creates an ast Name node.
    """
    return ast_mod.Name(id=id, ctx=ctx)


def util_json_builder():
    """
    Return: ast sub-tree of a function to read and parse json file:
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())
    """
    io_open = ast_mod.Call(func=ast_mod.Attribute(value=ast_name('io'), attr=ast_name('open')),
                           args=[ast_name('path')],
                           keywords=[ast_mod.keyword(arg='mode', value=ast_mod.Constant(value='r')),
                                     ast_mod.keyword(arg='encoding', value=ast_mod.Constant(value='utf-8'))])
    f_read = ast_mod.Call(ast_mod.Attribute(value=ast_name('f'), attr=ast_name('read')), args=[], keywords=[])
    return_node = ast_mod.Return(
        value=ast_mod.Call(func=ast_mod.Attribute(value=ast_name('json'), attr=ast_name('loads')),
                           args=[f_read],
                           keywords=[]))
    body = [
        ast_mod.With(
            items=[ast_mod.withitem(context_expr=io_open, optional_vars=ast_name('f'))],
            body=[ast_mod.Expr(value=return_node)])
    ]

    func = ast_mod.FunctionDef(
        name="util_load_json",
        args=ast_mod.arguments(
            posonlyargs=[], args=[ast_name('path')], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
        ),
        body=body,
        decorator_list=[],
        returns=None
    )
    return func


def args_builder(args_keys, input_args):
    """
    Args: args_keys: names of the arguments provided for the command
          input: dictionary of mocked inputs from the user
    Returns: ast node of type assign 'args = {test:'mock'}'
    """
    keys = []
    values = []
    if input_args:
        for arg in args_keys:
            keys.append(ast.Constant(value=arg))
            values.append(ast.Constant(value=input_args.get(arg)))
        return [ast_mod.Assign(targets=[ast_name('args', ctx=ast_mod.Store())],
                               value=ast.Dict(keys=keys, values=values))]
    return []


def request_mock_ast_builder(client_ast, client_calls):
    """
        Args: client_ast: Client class sun-ast.
                client_calls: all calls to method within the client class.
                directory_path: path to the directory contains the response
        Returns: ast nodes of requests mock.
    """
    mocks = []
    for call in client_calls:
        mocks.append(mock_response_ast_builder(call))
        suffix, method = get_call_params_from_http_request(client_ast, call)
        attr = ast_mod.Attribute(value=ast_name('requests_mock'),
                                 attr=ast_name(method.lower()))
        ret_val = ast_mod.keyword(arg=ast_name('json'),
                                  value=ast_name(f'mock_response_{call}'))
        mock_call = ast_mod.Call(func=attr,
                                 args=[ast_name(f'SERVER_URL + \'{suffix}\'')],
                                 keywords=[ret_val])
        mocks.append(ast_mod.Expr(value=mock_call))
    return mocks


def mock_response_ast_builder(call):
    """
    Args: call: name of the client function used in the call.
           directory_path: path to the outputs containing the mocked response from the API
    Return: Assign ast node of assignment of the mocked response to the mock_response object.
    """
    return ast_mod.Assign(targets=[ast_name(f'mock_response_{call}', ctx=ast_mod.Store())],
                          value=ast_mod.Call(func=ast_name('util_load_json'),
                                             args=[ast_mod.Constant(value=f'{DIRECTORY_PATH}/outputs/{call}.json')],
                                             keywords=[]))


def assertions_builder(call, ops, comperators):
    """
    Args: call: rhs of the assertions, item to check
            ops: operation to check
            comperators: values to check in the lhs
    Return: assert ast node
    """
    return ast_mod.Assert(test=ast_mod.Compare(left=call, ops=ops, comparators=comperators), msg=None)


def get_links(value):
    try:
        return value.links.func.attr
    except AttributeError:
        return None


def create_command_results_assertion(arg, value, command_name):
    """
    Inpust: arg: CommandResults argument
            value: CommandResults argument value
    Returns: Single assertion as part of command results assertions
    """
    comperator = None
    call = ast_mod.Attribute(value=ast_name('results'), attr=arg)
    ops = [ast_mod.Eq()]
    if hasattr(value, 'value'):
        # if so it is of type ast.Constant
        comperator = ast_mod.Constant(value=value.value)
    elif arg == 'raw_response':
        link = get_links(value)
        if link:
            comperator = ast_name(f'mock_response_{link}')
    return assertions_builder(call, ops, [comperator]) if comperator else None


def create_command_results_assertions(keywords, call):
    """
    Args: keywords: all the params passed to CommandResults object when created.
    Return: assertion for each of the CommandResults arg.
    """
    assertions = []
    for keyword in keywords:
        assertions.append(create_command_results_assertion(keyword.arg, keyword.value, call))
    return assertions


def instance_dict_parser(instance_dict, client_name):
    """
    Args: instance_dict: dictionary of the instances built in tree from the parser
            client_name: name of the client object
    Returns: args: list of arguments given as inputs to the function
             client_call: name of client function to mock
             command_result: CommandResults object returned from the command
    """
    args = []
    client_func_call = []
    for instance in instance_dict:
        try:
            func = str(instance.func)
            if func == 'args.get':
                args.append(instance.args[0].value)
            elif func.startswith(client_name):
                client_func_call.append(instance.func.attr)
        except AttributeError:
            pass
    return args, client_func_call


def get_mocked_args(command_name):
    """
    Args: command_name: name of the command.
           directory_path: path to the directory contains the file.
    Return: mocked command args json from input file.
    """
    path = f'{DIRECTORY_PATH}/inputs/{command_name}.json'
    if os.path.exists(path):
        args_dict = get_json(path)
        return args_dict
    return None


def get_call_params_from_http_request(client_ast, def_name):
    """
    Args: clinet_ast: sub ast of the Client class
            def_name: name of the client function that was called.
    Return: url suffix of the API request, call method (post/get)
    """
    method = 'POST'
    suffix = None
    for block in client_ast.body:
        if block.name == def_name:
            for node in block.body:
                if hasattr(node, 'value') and hasattr(node.value, 'func') and str(
                        node.value.func) == "self._http_request":
                    for key in node.value.keywords:
                        if hasattr(key, 'arg') and key.arg == 'method':
                            method = str(key.value).strip("\'")
                        if hasattr(key, 'arg') and key.arg == 'url_suffix':
                            suffix = str(key.value).strip("\'")
                else:
                    continue
    return suffix, method


def generate_test_client():
    """
        Return: client function to mock
    """
    body = [
        ast_mod.Return(value=ast_mod.Call(func=ast_name('Client'),
                                          args=[],
                                          keywords=[ast.keyword(arg='base_url', value=ast_name('SERVER_URL'))]))
    ]

    func = ast_mod.FunctionDef(
        name="client",
        args=ast_mod.arguments(
            posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
        ),
        body=body,
        decorator_list=[ast_mod.Call(func=ast_mod.Attribute(value=ast_name('pytest'), attr='fixture'),
                                     args=[],
                                     keywords=[])],
        returns=None
    )
    return func


def get_client_ast(tree):
    """
    Args: Ast tree of the input code.
    Return: Sub ast tree of the client class.
    """
    for body_node in tree.body:
        if hasattr(body_node, 'bases'):
            bases = [str(id) for id in body_node.bases]
            if 'BaseClient' in bases:
                return body_node
    return None


def get_client_name(func, client_class_name):
    """
    Args: func: ast node of the relevant function.
           client_class_name: name of the client class.
    Return: the name of the local client instance.
    """
    if hasattr(func.args, 'args'):
        for arg in func.args.args:
            if hasattr(arg, 'annotation') and str(arg.annotation) == client_class_name:
                return arg.arg
    return None


def get_return_values(func):
    """
    Args: function ast node
    Returns: array of ast nodes of returned values
    """
    for node in func.return_nodes:
        if hasattr(node, 'value') and hasattr(node.value, 'func') and str(node.value.func) == 'CommandResults':
            return node.value
    return None


def call_command_ast_builder(command_name, args):
    """
    Input: command_name: name of the command being called
    Returns: ast node of assignment command results to var.
    """
    call_args = [ast_name('client'), ast_name('args')] if len(args) > 0 else [ast_name('client')]
    return ast_mod.Assign(targets=[ast_name('results', ctx=ast_mod.Store())],
                          value=ast_mod.Call(func=ast_name(command_name),
                                             args=call_args,
                                             keywords=[]))


def generate_unit_test_decision_maker(command_name):
    """
    Returns true if unit test should be generated to a command, false otherwise
    """
    return len(COMMANDS) == 0 or command_name in COMMANDS


def build_imports(module_name, names_to_import):
    aliases = [ast_name(name) for name in names_to_import]
    return ast_mod.ImportFrom(module=module_name, names=aliases, level=0)


def generate_unit_tests(source, directory_path, module_name, commands, verbose=False):
    global DIRECTORY_PATH, COMMANDS, MODULE_NAME, VERBOSE
    DIRECTORY_PATH = directory_path
    COMMANDS = commands
    MODULE_NAME = module_name.split('.')[0]
    VERBOSE = verbose
    # tree = MANAGER.build_tree(ast_str=source)
    # cfg = MANAGER.build_cfg(tree)
    # cs = solver.ContractSolver(cfg, tree, "test")
    # MANAGER.logger.info("CONTRACT", "Running algorithm on file: {}", "test")
    # module = cs.solve()
    # output_test = astor.to_source(module.to_ast())
    output_test = None
    return output_test


if __name__ == "__main__":
    # source = """
    #     class Client(BaseClient):
    #         def malwarebazaar_comment_add_request(self, sha256_hash, comment):
    #             if self.api_key is None:
    #                 raise Exception('API Key is required for this command')
    #             response = self._http_request(method='POST',
    #                                           headers={"API-KEY": self.api_key},
    #                                           files={
    #                                               'query': (None, "add_comment"),
    #                                               'sha256_hash': (None, sha256_hash),
    #                                               'comment': (None, comment)
    #                                           },
    #                                           url_suffix='/login')
    #
    #             return response
    #         def malwarebazaar_test_request(self, sha256_hash, comment):
    #             if self.api_key is None:
    #                 raise Exception('API Key is required for this command')
    #             response = self._http_request(method='GET',
    #                                           headers={"API-KEY": self.api_key},
    #                                           files={
    #                                               'query': (None, "add_comment"),
    #                                               'sha256_hash': (None, sha256_hash),
    #                                               'comment': (None, comment)
    #                                           },
    #                                           url_suffix='/login222')
    #
    #             return response
    #
    #
    #     def malwarebazaar_comment_add_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    #         sha256_hash = args.get("sha256_hash")
    #         comment = args.get("comment")
    #         response = client.malwarebazaar_comment_add_request(sha256_hash, comment)
    #         results = client.malwarebazaar_test_request(arg1, arg2)
    #         check_query_status(response)
    #
    #         readable_output = f'Comment added to {sha256_hash} malware sample successfully'
    #         outputs = {
    #             'sha256_hash': sha256_hash,
    #             'comment': comment,
    #         }
    #         return CommandResults(
    #             outputs_prefix='MalwareBazaar.MalwarebazaarCommentAdd',
    #             outputs_key_field='sha256_hash',
    #             outputs=outputs,
    #             readable_output=readable_output,
    #             raw_response=response,
    #         )
    #     """
    source = """import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

requests.packages.urllib3.disable_warnings()

HOST_FIELDS = [
    'KLHST_WKS_FQDN',
    'KLHST_WKS_DNSNAME',
    'KLHST_WKS_HOSTNAME',
    'KLHST_WKS_OS_NAME',
    'KLHST_WKS_GROUPID',
    'KLHST_WKS_DNSDOMAIN',
    'KLHST_WKS_DN',
]

HOST_DETAILED_FIELDS = [
    'KLHST_WKS_DN',
    'KLHST_WKS_GROUPID',
    'KLHST_WKS_CREATED',
    'KLHST_WKS_LAST_VISIBLE',
    'KLHST_WKS_STATUS',
    'KLHST_WKS_HOSTNAME',
    'KLHST_INSTANCEID',
    'KLHST_WKS_DNSDOMAIN',
    'KLHST_WKS_DNSNAME',
    'KLHST_WKS_FQDN',
    'KLHST_WKS_CTYPE',
    'KLHST_WKS_PTYPE',
    'KLHST_WKS_OS_NAME',
    'KLHST_WKS_COMMENT',
    'KLHST_WKS_NAG_VERSION',
    'KLHST_WKS_RTP_AV_VERSION',
    'KLHST_WKS_RTP_AV_BASES_TIME',
    'KLHST_WKS_RBT_REQUIRED',
    'KLHST_WKS_RBT_REQUEST_REASON',
    'KLHST_WKS_OSSP_VER_MAJOR',
    'KLHST_WKS_OSSP_VER_MINOR',
    'KLHST_WKS_CPU_ARCH',
    'KLHST_WKS_OS_BUILD_NUMBER',
    'KLHST_WKS_OS_RELEASE_ID',
    'KLHST_WKS_NAG_VER_ID',
    'KLHST_WKS_OWNER_ID',
    'KLHST_WKS_OWNER_IS_CUSTOM',
    'KLHST_WKS_CUSTOM_OWNER_ID',
    'KLHST_WKS_ANTI_SPAM_STATUS',
    'KLHST_WKS_DLP_STATUS',
    'KLHST_WKS_COLLAB_SRVS_STATUS',
    'KLHST_WKS_EMAIL_AV_STATUS',
    'KLHST_WKS_EDR_STATUS',
]

GROUP_FIELDS = [
    'id',
    'name',
]

GROUP_DETAILED_FIELDS = [
    'id',
    'name',
    'parentId',
    'autoRemovePeriod',
    'notifyPeriod',
    'creationDate',
    'KLGRP_HlfInherited',
    'KLGRP_HlfForceChildren',
    'KLGRP_HlfForced',
    'lastUpdate',
    'hostsNum',
    'childGroupsNum',
    'grp_full_name',
    'level',
    'KLSRV_HSTSTAT_CRITICAL',
    'KLSRV_HSTSTAT_WARNING',
    'KLGRP_GRP_GROUPID_GP',
    'c_grp_autoInstallPackageId',
    'grp_from_unassigned',
    'grp_enable_fscan',
    'KLSRVH_SRV_DN',
    'KLVSRV_ID',
    'KLVSRV_DN',
    'KLGRP_CHLDGRP_CNT',
    'KLGRP_CHLDHST_CNT',
    'KLGRP_CHLDHST_CNT_OK',
    'KLGRP_CHLDHST_CNT_CRT',
    'KLGRP_CHLDHST_CNT_WRN',
]


class Client(BaseClient):
    def login(self, username: str, password: str) -> None:
        encoded_username = base64.b64encode(username.encode('utf-8')).decode('utf-8')
        encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        self._http_request(
            method='POST',
            url_suffix='/login',
            headers={
                'Authorization': f'KSCBasic user="{encoded_username}", pass="{encoded_password}"',
                'Content-Type': 'application/json',
            },
            resp_type='response'
        )

    def get_results(self, str_accessor: str, limit: Optional[int] = 50) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/ChunkAccessor.GetItemsChunk',
            json_data={
                'strAccessor': str_accessor,
                'nStart': 0,
                'nCount': limit,
            }
        )
        self._raise_for_error(response)
        return response

    def list_hosts_request(self,
                           wstr_filter: Optional[str] = None,
                           fields_to_return: Optional[List[str]] = None
                           ) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/HostGroup.FindHosts',
            json_data={
                'wstrFilter': wstr_filter,
                'lMaxLifeTime': 600,
                'vecFieldsToReturn': fields_to_return,
            }
        )
        self._raise_for_error(response)
        return response

    def list_groups_request(self,
                            wstr_filter: Optional[str] = None,
                            fields_to_return: Optional[List[str]] = None
                            ) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/HostGroup.FindGroups',
            json_data={
                'wstrFilter': wstr_filter,
                'lMaxLifeTime': 600,
                'vecFieldsToReturn': fields_to_return
            }
        )
        self._raise_for_error(response)
        return response

    def add_group_request(self,
                          name: str,
                          parent_id: Optional[int] = None,
                          ) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/HostGroup.AddGroup',
            json_data={
                'pInfo': {
                    'name': name,
                    'parentId': parent_id,
                }
            }
        )
        self._raise_for_error(response)
        return response

    def delete_group_request(self,
                             group_id: int,
                             flags: int = 1,
                             ) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/HostGroup.RemoveGroup',
            json_data={
                'nGroup': group_id,
                'nFlags': flags,
            }
        )
        self._raise_for_error(response)
        return response

    def list_software_applications_request(self) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/InventoryApi.GetInvProductsList',
        )
        self._raise_for_error(response)
        return response

    def list_software_patches_request(self) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/InventoryApi.GetInvPatchesList',
        )
        self._raise_for_error(response)
        return response

    def list_host_software_applications_request(self, hostname: str) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/InventoryApi.GetHostInvProducts',
            json_data={
                'szwHostId': hostname,
            }
        )
        self._raise_for_error(response)
        return response

    def list_host_software_patches_request(self, hostname: str) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/InventoryApi.GetHostInvPatches',
            json_data={
                'szwHostId': hostname
            }
        )
        self._raise_for_error(response)
        return response

    def list_policies_request(self, group_id: int) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/Policy.GetPoliciesForGroup',
            json_data={
                'nGroupId': group_id,
            }
        )
        self._raise_for_error(response)
        return response

    def get_policy_request(self, policy_id: int) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/Policy.GetPolicyData',
            json_data={
                'nPolicy': policy_id,
            }
        )
        self._raise_for_error(response)
        return response

    def get_action_status_request(self, action_id: str) -> Dict:
        response = self._http_request(
            method='POST',
            url_suffix='/AsyncActionStateChecker.CheckActionState',
            json_data={
                'wstrActionGuid': action_id,
            }
        )
        self._raise_for_error(response)
        return response


def list_hosts_command(client: Client, args: Dict) -> CommandResults:
    wstr_filter = args.get('filter')
    limit = arg_to_number(args.get('limit', 50))
    response = client.list_hosts_request(wstr_filter=wstr_filter, fields_to_return=HOST_FIELDS)
    str_accessor = response.get('strAccessor', '')
    results = client.get_results(str_accessor, limit)
    outputs = [host.get('value') for host in results.get('pChunk', {}).get('KLCSP_ITERATOR_ARRAY', [])]
    if not outputs:
        command_results_args = {'readable_output': 'No hosts found.'}
    else:
        command_results_args = {
            'outputs_prefix': 'KasperskySecurityCenter.Host',
            'outputs_key_field': 'KLHST_WKS_HOSTNAME',
            'outputs': outputs,  # type: ignore[dict-item]
            'readable_output': tableToMarkdown(
                'Hosts List',
                outputs,
                ['KLHST_WKS_HOSTNAME', 'KLHST_WKS_DN', 'KLHST_WKS_OS_NAME', 'KLHST_WKS_FQDN']
            ),
            'raw_response': results,  # type: ignore[dict-item]
        }
    return CommandResults(**command_results_args)  # type: ignore[arg-type]
"""
    tree = MANAGER.build_tree(ast_str=source)
    tree2 = klara.parse(source)
    # cfg = MANAGER.build_cfg(tree)
    # cs = solver.ContractSolver(cfg, tree, "test")
    # MANAGER.logger.info("CONTRACT", "Running algorithm on file: {}", "test")
    # module = cs.solve(
    #     '/Users/epintzov/dev/demisto/demisto-sdk/demisto_sdk/commands/generate_unit_tests/tests/test_files')
    # output_test = astor.to_source(module.to_ast())
    x = 2
