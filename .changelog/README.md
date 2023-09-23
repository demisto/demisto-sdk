## Changelog management
Every development in the Demisto SDK repository requires documentation.

To document a change/addition, follow these steps:
- Commit and push your changes to the remote branch.
- Open a pull request.
- Run the command `sdk-changelog —init —pr_number <pr number>`.
- Edit the generated YAML file with the documentation of your changes.

#### Types:

- `breaking`: A change with backward compatibility break.
- `feature`: Adding a new feature.
- `fix`: Bugfix.
- `internal`: Adding, changing, or fixing internal components.

Note: In cases where there are multiple changes in the pull request, you can add additional documentation with a specific type for each.