from github import Github
import os
from github import Auth


# using an access token

# Public Web Github
g = Github(login_or_token=os.getenv("TOKEN"), verify=False)
repo = g.get_repo("demisto/demisto-sdk")

workflow_run = repo.get_workflow_run("WORKFLOW-RUN")


jobs = [job for job in workflow_run.jobs()]

print()

