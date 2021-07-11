import demistomock as demisto
from CommonServerPython import *


class Client(BaseClient):
    def __init__(self, server_url, verify, proxy, headers, auth):
        super().__init__(base_url=server_url, verify=verify,
                         proxy=proxy, headers=headers, auth=auth)

    def add_pet_request(self, pet_id, pet_category, pet_name, pet_photourls, pet_tags, pet_status):
        data = assign_params(id=pet_id, category=pet_category, name=pet_name,
                             photoUrls=pet_photourls, tags=pet_tags, status=pet_status)
        headers = self._headers

        response = self._http_request(
            'post', 'pet', json_data=data, headers=headers)

        return response

    def create_user_request(self, user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus):
        data = assign_params(id=user_id, username=user_username, firstName=user_firstname, lastName=user_lastname,
                             email=user_email, password=user_password, phone=user_phone, userStatus=user_userstatus)
        headers = self._headers

        response = self._http_request(
            'post', 'user', json_data=data, headers=headers)

        return response

    def create_users_with_array_input_request(self, user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus):
        data = assign_params(id=user_id, username=user_username, firstName=user_firstname, lastName=user_lastname,
                             email=user_email, password=user_password, phone=user_phone, userStatus=user_userstatus)
        headers = self._headers

        response = self._http_request(
            'post', 'user/createWithArray', json_data=data, headers=headers)

        return response

    def create_users_with_list_input_request(self, user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus):
        data = assign_params(id=user_id, username=user_username, firstName=user_firstname, lastName=user_lastname,
                             email=user_email, password=user_password, phone=user_phone, userStatus=user_userstatus)
        headers = self._headers

        response = self._http_request(
            'post', 'user/createWithList', json_data=data, headers=headers)

        return response

    def delete_order_request(self, orderId):
        headers = self._headers

        response = self._http_request(
            'delete', f'store/order/{orderId}', headers=headers)

        return response

    def delete_pet_request(self, api_key, petId):
        headers = self._headers

        response = self._http_request(
            'delete', f'pet/{petId}', headers=headers)

        return response

    def delete_user_request(self, username):
        headers = self._headers

        response = self._http_request(
            'delete', f'user/{username}', headers=headers)

        return response

    def find_pets_by_status_request(self, status):
        params = assign_params(status=status)
        headers = self._headers

        response = self._http_request(
            'get', 'pet/findByStatus', params=params, headers=headers)

        return response

    def find_pets_by_tags_request(self, tags):
        params = assign_params(tags=tags)
        headers = self._headers

        response = self._http_request(
            'get', 'pet/findByTags', params=params, headers=headers)

        return response

    def get_inventory_request(self):
        headers = self._headers

        response = self._http_request(
            'get', 'store/inventory', headers=headers)

        return response

    def get_order_by_id_request(self, orderId):
        headers = self._headers

        response = self._http_request(
            'get', f'store/order/{orderId}', headers=headers)

        return response

    def get_pet_by_id_request(self, petId):
        headers = self._headers

        response = self._http_request('get', f'pet/{petId}', headers=headers)

        return response

    def get_user_by_name_request(self, username):
        headers = self._headers

        response = self._http_request(
            'get', f'user/{username}', headers=headers)

        return response

    def login_user_request(self, username, password):
        params = assign_params(username=username, password=password)
        headers = self._headers

        response = self._http_request(
            'get', 'user/login', params=params, headers=headers)

        return response

    def logout_user_request(self):
        headers = self._headers

        response = self._http_request('get', 'user/logout', headers=headers)

        return response

    def place_order_request(self, order_id, order_petid, order_quantity, order_shipdate, order_status, order_complete):
        data = assign_params(id=order_id, petId=order_petid, quantity=order_quantity,
                             shipDate=order_shipdate, status=order_status, complete=order_complete)
        headers = self._headers

        response = self._http_request(
            'post', 'store/order', json_data=data, headers=headers)

        return response

    def post_pet_upload_image_request(self, petId, additionalMetadata, file):
        data = assign_params(additionalMetadata=additionalMetadata, file=file)
        headers = self._headers
        headers['Content-Type'] = 'multipart/form-data'

        response = self._http_request(
            'post', f'pet/{petId}/uploadImage', json_data=data, headers=headers)

        return response

    def post_pet_upload_image_by_uploadimage_request(self, petId, additionalMetadata, file):
        data = assign_params(additionalMetadata=additionalMetadata, file=file)
        headers = self._headers
        headers['Content-Type'] = 'multipart/form-data'

        response = self._http_request(
            'post', f'pet/{petId}/uploadImage/{uploadimage}', json_data=data, headers=headers)

        return response

    def update_pet_request(self, pet_id, pet_category, pet_name, pet_photourls, pet_tags, pet_status):
        data = assign_params(id=pet_id, category=pet_category, name=pet_name,
                             photoUrls=pet_photourls, tags=pet_tags, status=pet_status)
        headers = self._headers

        response = self._http_request(
            'put', 'pet', json_data=data, headers=headers)

        return response

    def update_pet_with_form_request(self, petId, name, status):
        data = assign_params(name=name, status=status)
        headers = self._headers
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        response = self._http_request(
            'post', f'pet/{petId}', json_data=data, headers=headers)

        return response

    def update_user_request(self, username, user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus):
        data = assign_params(id=user_id, username=user_username, firstName=user_firstname, lastName=user_lastname,
                             email=user_email, password=user_password, phone=user_phone, userStatus=user_userstatus)
        headers = self._headers

        response = self._http_request(
            'put', f'user/{username}', json_data=data, headers=headers)

        return response


def add_pet_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    pet_id = args.get('pet_id', None)
    pet_category_id = args.get('pet_category_id', None)
    pet_category_name = str(args.get('pet_category_name', ''))
    pet_category = assign_params(id=pet_category_id, name=pet_category_name)
    pet_name = str(args.get('pet_name', ''))
    pet_photourls = argToList(args.get('pet_photourls', []))
    pet_tags = argToList(args.get('pet_tags', []))
    pet_status = str(args.get('pet_status', ''))

    response = client.add_pet_request(
        pet_id, pet_category, pet_name, pet_photourls, pet_tags, pet_status)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def create_user_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    user_id = args.get('user_id', None)
    user_username = str(args.get('user_username', ''))
    user_firstname = str(args.get('user_firstname', ''))
    user_lastname = str(args.get('user_lastname', ''))
    user_email = str(args.get('user_email', ''))
    user_password = str(args.get('user_password', ''))
    user_phone = str(args.get('user_phone', ''))
    user_userstatus = args.get('user_userstatus', None)

    response = client.create_user_request(
        user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def create_users_with_array_input_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    user_id = args.get('user_id', None)
    user_username = str(args.get('user_username', ''))
    user_firstname = str(args.get('user_firstname', ''))
    user_lastname = str(args.get('user_lastname', ''))
    user_email = str(args.get('user_email', ''))
    user_password = str(args.get('user_password', ''))
    user_phone = str(args.get('user_phone', ''))
    user_userstatus = args.get('user_userstatus', None)

    response = client.create_users_with_array_input_request(
        user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def create_users_with_list_input_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    user_id = args.get('user_id', None)
    user_username = str(args.get('user_username', ''))
    user_firstname = str(args.get('user_firstname', ''))
    user_lastname = str(args.get('user_lastname', ''))
    user_email = str(args.get('user_email', ''))
    user_password = str(args.get('user_password', ''))
    user_phone = str(args.get('user_phone', ''))
    user_userstatus = args.get('user_userstatus', None)

    response = client.create_users_with_list_input_request(
        user_id, user_username, user_firstname, user_lastname, user_email, user_password, user_phone, user_userstatus)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def delete_order_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    orderId = args.get('orderId', None)

    response = client.delete_order_request(orderId)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def delete_pet_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    api_key = str(args.get('api_key', ''))
    petId = args.get('petId', None)

    response = client.delete_pet_request(api_key, petId)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def delete_user_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    username = str(args.get('username', ''))

    response = client.delete_user_request(username)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def find_pets_by_status_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    status = argToList(args.get('status', []))

    response = client.find_pets_by_status_request(status)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.None',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def find_pets_by_tags_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    tags = argToList(args.get('tags', []))

    response = client.find_pets_by_tags_request(tags)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.Pet',
        outputs_key_field='id',
        outputs=response,
        raw_response=response
    )

    return command_results


def get_inventory_command(client: Client, args: Dict[str, Any]) -> CommandResults:

    response = client.get_inventory_request()
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def get_order_by_id_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    orderId = args.get('orderId', None)

    response = client.get_order_by_id_request(orderId)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.Order',
        outputs_key_field='id',
        outputs=response,
        raw_response=response
    )

    return command_results


def get_pet_by_id_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    petId = args.get('petId', None)

    response = client.get_pet_by_id_request(petId)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.Pet',
        outputs_key_field='id',
        outputs=response,
        raw_response=response
    )

    return command_results


def get_user_by_name_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    username = str(args.get('username', ''))

    response = client.get_user_by_name_request(username)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.User',
        outputs_key_field='id',
        outputs=response,
        raw_response=response
    )

    return command_results


def login_user_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    username = str(args.get('username', ''))
    password = str(args.get('password', ''))

    response = client.login_user_request(username, password)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def logout_user_command(client: Client, args: Dict[str, Any]) -> CommandResults:

    response = client.logout_user_request()
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def place_order_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    order_id = args.get('order_id', None)
    order_petid = args.get('order_petid', None)
    order_quantity = args.get('order_quantity', None)
    order_shipdate = str(args.get('order_shipdate', ''))
    order_status = str(args.get('order_status', ''))
    order_complete = argToBoolean(args.get('order_complete', False))

    response = client.place_order_request(
        order_id, order_petid, order_quantity, order_shipdate, order_status, order_complete)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.Order',
        outputs_key_field='id',
        outputs=response,
        raw_response=response
    )

    return command_results


def post_pet_upload_image_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    petId = args.get('petId', None)
    additionalMetadata = str(args.get('additionalMetadata', ''))
    file = str(args.get('file', ''))

    response = client.post_pet_upload_image_request(
        petId, additionalMetadata, file)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.ApiResponse',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def post_pet_upload_image_by_uploadimage_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    petId = args.get('petId', None)
    additionalMetadata = str(args.get('additionalMetadata', ''))
    file = str(args.get('file', ''))

    response = client.post_pet_upload_image_by_uploadimage_request(
        petId, additionalMetadata, file)
    command_results = CommandResults(
        outputs_prefix='TestSwagger.ApiResponse',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def update_pet_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    pet_id = args.get('pet_id', None)
    pet_category_id = args.get('pet_category_id', None)
    pet_category_name = str(args.get('pet_category_name', ''))
    pet_category = assign_params(id=pet_category_id, name=pet_category_name)
    pet_name = str(args.get('pet_name', ''))
    pet_photourls = argToList(args.get('pet_photourls', []))
    pet_tags = argToList(args.get('pet_tags', []))
    pet_status = str(args.get('pet_status', ''))

    response = client.update_pet_request(
        pet_id, pet_category, pet_name, pet_photourls, pet_tags, pet_status)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def update_pet_with_form_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    petId = args.get('petId', None)
    name = str(args.get('name', ''))
    status = str(args.get('status', ''))

    response = client.update_pet_with_form_request(petId, name, status)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def update_user_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    username = str(args.get('username', ''))
    user_id = args.get('user_id', None)
    user_username = str(args.get('user_username', ''))
    user_firstname = str(args.get('user_firstname', ''))
    user_lastname = str(args.get('user_lastname', ''))
    user_email = str(args.get('user_email', ''))
    user_password = str(args.get('user_password', ''))
    user_phone = str(args.get('user_phone', ''))
    user_userstatus = args.get('user_userstatus', None)

    response = client.update_user_request(username, user_id, user_username, user_firstname,
                                          user_lastname, user_email, user_password, user_phone, user_userstatus)
    command_results = CommandResults(
        outputs_prefix='TestSwagger',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def test_module(client: Client) -> None:
    # Test functions here
    return_results('ok')


def main():

    params: Dict[str, Any] = demisto.params()
    args: Dict[str, Any] = demisto.args()
    url = params.get('url')
    verify_certificate: bool = not params.get('insecure', False)
    proxy = params.get('proxy', False)
    headers = {}
    headers['Authorization'] = params['api_key']

    command = demisto.command()
    demisto.debug(f'Command being called is {command}')

    try:
        requests.packages.urllib3.disable_warnings()
        client: Client = Client(
            urljoin(url, '/v2'), verify_certificate, proxy, headers=headers, auth=None)

        commands = {
            'testswagger-add-pet': add_pet_command,
            'testswagger-create-user': create_user_command,
            'testswagger-create-users-with-array-input': create_users_with_array_input_command,
            'testswagger-create-users-with-list-input': create_users_with_list_input_command,
            'testswagger-delete-order': delete_order_command,
            'testswagger-delete-pet': delete_pet_command,
            'testswagger-delete-user': delete_user_command,
            'testswagger-find-pets-by-status': find_pets_by_status_command,
            'testswagger-find-pets-by-tags': find_pets_by_tags_command,
            'testswagger-get-inventory': get_inventory_command,
            'testswagger-get-order-by-id': get_order_by_id_command,
            'testswagger-get-pet-by-id': get_pet_by_id_command,
            'testswagger-get-user-by-name': get_user_by_name_command,
            'testswagger-login-user': login_user_command,
            'testswagger-logout-user': logout_user_command,
            'testswagger-place-order': place_order_command,
            'testswagger-post-pet-upload-image': post_pet_upload_image_command,
            'testswagger-post-pet-upload-image-by-uploadimage': post_pet_upload_image_by_uploadimage_command,
            'testswagger-update-pet': update_pet_command,
            'testswagger-update-pet-with-form': update_pet_with_form_command,
            'testswagger-update-user': update_user_command,
        }

        if command == 'test-module':
            test_module(client)
        elif command in commands:
            return_results(commands[command](client, args))
        else:
            raise NotImplementedError(f'{command} command is not implemented.')

    except Exception as e:
        return_error(str(e))


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()
