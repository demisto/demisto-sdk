### Convert JSON to Demisto Outputs
Convert JSON format to demisto entry context yaml format.

**Arguments**:
* *-c, --command*
    Command name (e.g. xdr-get-incidents)
* *-i, --input*
    A JSON file path. If not specified then script will wait for user input in the terminal.
* *-p, --prefix*
    Output prefix like Jira.Ticket, VirusTotal.IP
* *-o, --output*
    Output file path, if not specified then will print to stdout
* *-v, --verbose*
    Verbose output - mainly for debugging purposes
* *-int, --interactive*
    If passed, then for each output field will ask user interactively to enter the description. By default is interactive mode is disabled
* *-d, --description-json*
    A JSON or a path to a JSON file, mapping field names to their descriptions.

**Examples**:
<br/>`demisto-sdk json-to-outputs -c jira-get-ticket -p Jira.Ticket -i path/to/valid.json`
<br/>if valid.json looks like
```json
{
    "id": 100,
    "title": "do something title",
    "created_at": "2019-01-01T00:00:00"
}
```
This command will print to the stdout the following:
```yaml
arguments: []
name: jira-get-ticket
outputs:
- contextPath: Jira.Ticket.id
  description: ''
  type: Number
- contextPath: Jira.Ticket.title
  description: ''
  type: String
- contextPath: Jira.Ticket.created_at
  description: ''
  type: Date
```
