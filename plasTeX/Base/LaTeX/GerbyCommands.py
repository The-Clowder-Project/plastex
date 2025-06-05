# plasTeX/Base/LaTeX/GerbyCommands.py

from plasTeX import Command

class ProofBox(Command):
    """
    A custom LaTeX command \ProofBox{content}.
    The content passed to this command will become the children
    of this ProofBox node in the document model.
    """
    # The 'args' attribute defines how LaTeX arguments are parsed.
    # 'self' is a special value: it means the content of the
    # (single, mandatory) argument to \ProofBox becomes the direct
    # children of this ProofBox node instance.
    args = 'self'
