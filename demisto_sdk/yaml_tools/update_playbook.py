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


def replace_version(playbook):
    """Replaces the version of playbook with -1

    Args:
        playbook: playbook dict loaded from yaml

    Returns:
        Dict. updated playbook dict

    """
    playbook['version'] = -1

    return playbook


def update_id_to_be_equal_name(playbook):
    """Updates the id of the playbook to be the same as playbook name.

    The reason for that is that demisto generates id - uuid for playbooks/scripts/integrations

    Args:
        playbook: playbook dict loaded from yaml

    Returns:
        Dict. updated playbook dict

    """
    playbook['id'] = playbook['name']

    return playbook





def update_playbook(source_path, destination_path):
    print(F'Starting update playbook for {source_path}')

    with open(source_path) as f:
        playbook = yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    playbook = update_replace_copy_dev(playbook)

    # add description to tasks that shouldn't have description like start, end, title
    playbook = add_description(playbook)

    # update the name of playbooks tasks to be equal to the name of the playbook
    playbook = update_playbook_task_name(playbook)

    # replace version to be -1
    playbook = replace_version(playbook)

    playbook = update_id_to_be_equal_name(playbook)

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


def main(argv):
    if len(argv) < 1:
        print('Please provide <source playbook path>, <optional - destination playbook path>')
        sys.exit(1)

    source_path = argv[0]
    destination_path = argv[1] if len(argv) >= 2 else ''

    update_playbook(source_path, destination_path)


if __name__ == '__main__':
    main(sys.argv[1:])
