# plasTeX/Base/LaTeX/GerbyCommands.py

from plasTeX import Command

class ProofBox(Command):
    """
    A custom LaTeX command \ProofBox{content}.
    """
    args = 'self'

class scalemath(Command):
    """
    A custom LaTeX command \scalemath{id}.
    """
    args = 'self'

class webcompile(Command):
    """
    A custom LaTeX command \webcompile{id}.
    """
    args = 'self'

class tikzcdid(Command):
    """
    A custom LaTeX command \tikzcdid{id}.
    """
    args = 'self'

class rowcolor(Command):
    """
    A custom LaTeX command \rowcolor{id}.
    """
    args = 'self'

class Gape(Command):
    """
    A custom LaTeX command \Gape[one][two].
    """
    args = '[one] [two]'
