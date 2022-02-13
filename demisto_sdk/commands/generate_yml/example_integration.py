from generate_yml import DecoratorsStuff

decorators = DecoratorsStuff()


@decorators.add_command(command_name='first_command')
def this_is_a_command():
    """Some Documentation"""
    print("hello")
