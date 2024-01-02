## Changelog management
Each modification or addition in the Demisto SDK repository necessitates corresponding documentation.
To document your changes, adhere to the following steps:

### Init:
- Commit and push your alterations to the remote branch.
- Initiate a pull request.
- Execute the command `sdk-changelog —-init -n <pr number>`.
  - It will create `<pr number>.yml` file with the following starting template:
    ```
    changes:
    - description: enter description about this PR
      type: <fix|feature|breaking|internal>
    pr_number: 'xxxx'
    ```
- Go to the generated YAML file:
  - Add a description for the changes made in the PR
  - Update the type field based on the type of changes made

###### Types:

- `breaking`: A change with backward compatibility break.
- `feature`: Adding a new feature.
- `fix`: Bugfix.
- `internal`: Adding, changing, or fixing internal components.

In cases where there are multiple changes in the pull request, you can add additional documentation with a specific type for each, for example:
```
changes:
- description: Example for description 1.
  type: feature
- description: Example for description 2.
  type: fix
pr_number: '1111'
```

### Validate
Validate the log file by executing the command:
`sdk-changelog --validate -n <pr number>`