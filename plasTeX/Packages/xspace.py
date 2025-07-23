from plasTeX import Command

class xspace(Command):
    r"""
    A placeholder node for the \xspace command.
    The rendering logic is handled by the template.
    """
    # \xspace takes no arguments.
    args = ''
