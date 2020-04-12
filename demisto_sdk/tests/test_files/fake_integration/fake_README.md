Use the Zoom integration manage your Zoom users and meetings
This integration was integrated and tested with version xx of Zoom
## Configure Zoom on Demisto

1. Navigate to **Settings** > **Integrations** > **Servers & Services**.
2. Search for Zoom.
3. Click **Add instance** to create and configure a new integration instance.

| **Parameter** | **Description** | **Required** |
| --- | --- | --- |
| apiKey |  | True |
| apiSecret |  | True |
| proxy | Use system proxy settings | False |

4. Click **Test** to validate the URLs, token, and connection.
## Commands
You can execute these commands from the Demisto CLI, as part of an automation, or in a playbook.
After you successfully execute a command, a DBot message appears in the War Room with the command details.
### zoom-create-user
***
Create a new user in zoom account


##### Base Command

`zoom-create-user`
##### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| first_name | First name of the new user | Required | 
| last_name | Last name of the new user | Required | 
| email | The email of the new user | Required | 
| user_type | The type of the newly created user | Optional | 


##### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Zoom.User.id | string | The ID of the created user | 
| Zoom.User.first_name | string | First name of the created user | 
| Zoom.User.last_name | string | Last name for the created user | 
| Zoom.User.email | string | Email of the created user | 
| Zoom.User.created_at | date | Created date of the user | 
| Zoom.User.type | number | The type of the user | 


##### Command Example
``` ```

##### Human Readable Output


### zoom-create-meeting
***
Create a new zoom meeting (scheduled or instant)


##### Base Command

`zoom-create-meeting`
##### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| type | The type of the meeting | Required | 
| user | email address or id of user for meeting | Required | 
| topic | The topic of the meeting | Required | 
| auto-record-meeting | Record zoom meeting?  | Optional | 
| start-time | Meeting start time. When using a format like “yyyy-MM-dd’T&#x27;HH:mm:ss&#x27;Z’”, always use GMT time. When using a format like “yyyy-MM-dd’T&#x27;HH:mm:ss”, you should use local time and you will need to specify the time zone. Only used for scheduled meetings and recurring meetings with fixed time. | Optional | 
| timezone | Timezone to format start_time. For example, “America/Los_Angeles”. For scheduled meetings only.  | Optional | 


##### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| Zoom.Meeting.join_url | string | Join url for the meeting | 
| Zoom.Meeting.id | string | Meeting id of the new meeting that is created | 
| Zoom.Meeting.start_url | string | The URL to start the meeting | 


##### Command Example
``` ```

##### Human Readable Output


### zoom-fetch-recording
***
Get meeting record and save as file in the warroom


##### Base Command

`zoom-fetch-recording`
##### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| meeting_id | Meeting id to get the recording | Required | 


##### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| File.SHA256 | unknown | Attachment&\#x27;s SHA256 | 
| File.SHA1 | unknown | Attachment&\#x27;s SHA1 | 
| File.MD5 | unknown | Attachment&\#x27;s MD5 | 
| File.Name | unknown | Attachment&\#x27;s Name | 
| File.Info | unknown | Attachment&\#x27;s Info | 
| File.Size | unknown | Attachment&\#x27;s Size \(In Bytes\) | 
| File.Extension | unknown | Attachment&\#x27;s Extension | 
| File.Type | unknown | Attachment&\#x27;s Type | 
| File.EntryID | unknown | Attachment&\#x27;s EntryID | 
| File.SSDeep | unknown | Attachment&\#x27;s SSDeep hash | 


##### Command Example
``` ```

##### Human Readable Output


### zoom-list-users
***
List the existing users


##### Base Command

`zoom-list-users`
##### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| status | Which status of users to list | Optional | 
| page-size | Number of users to return. Max 300. | Optional | 
| page-number | Which page of results to return | Optional | 


##### Context Output

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


##### Command Example
``` ```

##### Human Readable Output


### zoom-delete-user
***
Delete a user from Zoom


##### Base Command

`zoom-delete-user`
##### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| user | The user ID or email to delete | Required | 
| action | The action to take | Optional | 


##### Context Output

There is no context output for this command.

##### Command Example
``` ```

##### Human Readable Output

