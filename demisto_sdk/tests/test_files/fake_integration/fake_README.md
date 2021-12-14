Use the Zoom integration manage your Zoom users and meetings
This integration was integrated and tested with version xx of Zoom

## Configure Zoom on Cortex XSOAR

1. Navigate to **Settings** > **Integrations** > **Servers & Services**.
2. Search for Zoom.
3. Click **Add instance** to create and configure a new integration instance.

    | **Parameter** | **Description** | **Required** |
    | --- | --- | --- |
    | apiKey |  | True |
    | apiSecret |  | True |
    | Use system proxy settings | additional data | False |

4. Click **Test** to validate the URLs, token, and connection.
## Commands
You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.
After you successfully execute a command, a DBot message appears in the War Room with the command details.
### zoom-create-user
***
Create a new user in zoom account


#### Base Command

`zoom-create-user`
#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| first_name | First name of the new user. | Required | 
| last_name | Last name of the new user. | Required | 
| email | The email of the new user. | Required | 
| user_type | The type of the newly created user. Possible values are: Basic, Pro, Corporate. Default is Basic. | Optional | 


#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Zoom.User.id | string | The ID of the created user | 
| Zoom.User.first_name | string | First name of the created user | 
| Zoom.User.last_name | string | Last name for the created user | 
| Zoom.User.email | string | Email of the created user | 
| Zoom.User.created_at | date | Created date of the user | 
| Zoom.User.type | number | The type of the user | 

#### Command example
```!zoom-create-user first_name=test1 last_name=test2 email=test@test.com user_type=Basic```
#### Context Example
```json
{
    "first_name": "test1",
    "last_name": "test2",
    "email": "test@test.com",
    "user_type": "Basic"
}
```

#### Human Readable Output

>first_name | last_name | email | user_type
>--- | --- | --- | ---
>test1 | test2 | test@test.com | Basic

#### Command example
```!zoom-create-user first_name=test1 last_name=test2 email=test@test.com user_type=Pro```
#### Context Example
```json
{
    "first_name": "test1",
    "last_name": "test2",
    "email": "test@test.com",
    "user_type": "Pro"
}
```

#### Human Readable Output

>first_name | last_name | email | user_type
>--- | --- | --- | ---
>test1 | test2 | test@test.com | Pro

### zoom-create-meeting
***
Create a new zoom meeting (scheduled or instant)


#### Base Command

`zoom-create-meeting`
#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| type | The type of the meeting. Possible values are: Instant, Scheduled. Default is Instant. | Required | 
| user | email address or id of user for meeting. | Required | 
| topic | The topic of the meeting. | Required | 
| auto-record-meeting | Record zoom meeting? . Possible values are: yes, no. Default is no. | Optional | 
| start-time | Meeting start time. When using a format like “yyyy-MM-dd’T'HH:mm:ss'Z’”, always use GMT time. When using a format like “yyyy-MM-dd’T'HH:mm:ss”, you should use local time and you will need to specify the time zone. Only used for scheduled meetings and recurring meetings with fixed time. | Optional | 
| timezone | Timezone to format start_time. For example, “America/Los_Angeles”. For scheduled meetings only. . | Optional | 


#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Zoom.Meeting.join_url | string | Join url for the meeting | 
| Zoom.Meeting.id | string | Meeting id of the new meeting that is created | 
| Zoom.Meeting.start_url | string | The URL to start the meeting | 

#### Command example
```!zoom-create-meeting type=Instant user=test@test.com topic=mytopic```
#### Context Example
```json
{
    "type": "Instant",
    "user": "test@test.com",
    "topic": "mytopic"
}
```

#### Human Readable Output

>type | user | topic
>--- | --- | ---
>Instant | test@test.com | mytopic

### zoom-fetch-recording
***
Get meeting record and save as file in the warroom


#### Base Command

`zoom-fetch-recording`
#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| meeting_id | Meeting id to get the recording. | Required | 


#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| File.SHA256 | unknown | Attachment's SHA256 | 
| File.SHA1 | unknown | Attachment's SHA1 | 
| File.MD5 | unknown | Attachment's MD5 | 
| File.Name | unknown | Attachment's Name | 
| File.Info | unknown | Attachment's Info | 
| File.Size | unknown | Attachment's Size \(In Bytes\) | 
| File.Extension | unknown | Attachment's Extension | 
| File.Type | unknown | Attachment's Type | 
| File.EntryID | unknown | Attachment's EntryID | 
| File.SSDeep | unknown | Attachment's SSDeep hash | 

#### Command example
```!zoom-fetch-recording meeting_id=1```
#### Context Example
```json
{
    "meeting_id": "1"
}
```

#### Human Readable Output

>meeting_id
>---
>1

### zoom-list-users
***
List the existing users


#### Base Command

`zoom-list-users`
#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| status | Which status of users to list. Possible values are: active, inactive, pending. Default is active. | Optional | 
| page-size | Number of users to return. Max 300. Default is 30. | Optional | 
| page-number | Which page of results to return. Default is 1. | Optional | 


#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Zoom.Metadata.Count | number | Total page count available | 
| Zoom.Metadata.Number | number | Current page number | 
| Zoom.Metadata.Size | number | Number of results in current page | 
| Zoom.Metadata.Total | number | Total number of records | 
| Zoom.User.id | string | ID of the user | 
| Zoom.User.first_name | string | First name of user | 
| Zoom.User.last_name | string | Last name of user | 
| Zoom.User.email | string | Email of user | 
| Zoom.User.type | number | Type of user | 
| Zoom.User.created_at | date | Date when user was created | 
| Zoom.User.dept | string | Department for user | 
| Zoom.User.verified | number | Is the user verified | 
| Zoom.User.last_login_time | date | Last login time of the user | 
| Zoom.User.timezone | string | Default timezone for the user | 
| Zoom.User.pmi | string | PMI of user | 
| Zoom.User.group_ids | string | Groups user belongs to | 

#### Command example
```!zoom-list-users```
#### Human Readable Output

>
>


### zoom-delete-user
***
Delete a user from Zoom


#### Base Command

`zoom-delete-user`
#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| user | The user ID or email to delete. | Required | 
| action | The action to take. Possible values are: disassociate, delete. Default is disassociate. | Optional | 


#### Context Output

There is no context output for this command.
#### Command example
```!zoom-delete-user user=test@test.com```
#### Context Example
```json
{
    "user": "test@test.com"
}
```

#### Human Readable Output

>user
>---
>test@test.com
