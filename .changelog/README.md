## Changelog management
Each modification or addition in the Demisto SDK repository necessitates corresponding documentation. To document your changes, adhere to the following steps:

- Commit and push your alterations to the remote branch.
- Initiate a pull request.
- Execute the command `sdk-changelog —init —pr_number <pr number>`, This will create a YAML file with the following starting template:
```

```
- Amend the generated YAML file to incorporate the documentation for your changes.

#### Types:

- `breaking`: A change with backward compatibility break.
- `feature`: Adding a new feature.
- `fix`: Bugfix.
- `internal`: Adding, changing, or fixing internal components.

In cases where there are multiple changes in the pull request, you can add additional documentation with a specific type for each, for example:
```
logs:
- description: Example for description 1.
  type: feature
- description: Example for description 2.
  type: fix
pr_number: '1111'
```