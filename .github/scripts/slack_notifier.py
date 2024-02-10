from github import Github
import os
from github import Auth


# using an access token
# First create a Github instance:

# Public Web Github
g = Github(login_or_token=os.getenv("TOKEN"), verify=False)
repo = g.get_repo("demisto/demisto-sdk")

workflow_run = repo.get_workflow_run(7812214569)


jobs = [job for job in workflow_run.jobs()]

print()

