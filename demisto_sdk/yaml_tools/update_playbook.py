import sys
import ntpath
import yaml
import yamlordereddictloader


def add_description(playbook):
    """Add empty description to tasks of type title, start, end

    Args:
        playbook: playbook dict loaded from yaml

    Returns:
        Dict. updated playbook dict
    """
    possible_labels_to_modify = ['start', 'end', 'title', 'playbook']

    for task_id, task in playbook.get('tasks', {}).items():
        if task.get('type', '') in possible_labels_to_modify:
            task['task']['description'] = ''

    return playbook


def update_playbook_task_name(playbook):
    """Updates the name of the task to be the same as playbookName it is running

    Args:
        playbook: playbook dict loaded from yaml

    Returns:
        Dict. updated playbook dict
    """
    for task_id, task in playbook.get('tasks', {}).items():
        if task.get('type', '') == 'playbook':
            task['task']["name"] = task['task']['playbookName']

    return playbook


def update_playbook(source_path, destination_path):
    print(F'Starting update playbook for {source_path}')

    with open(source_path) as f:
        playbook = yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    playbook = add_description(playbook)
    playbook = update_playbook_task_name(playbook)

    if not destination_path:
        destination_path = ntpath.basename(source_path)

    if not destination_path.startswith('playbook-'):
        destination_path = F'playbook-{destination_path}'

    # Configure safe dumper (multiline for strings)
    yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str

    def repr_str(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
        return dumper.org_represent_str(data)
    yaml.add_representer(str, repr_str, Dumper=yamlordereddictloader.SafeDumper)

    with open(destination_path, 'w') as f:
        yaml.dump(
            playbook,
            f,
            Dumper=yamlordereddictloader.SafeDumper,
            default_flow_style=False)

    print(F'Finished updating {source_path} - new yml saved at {destination_path}')
