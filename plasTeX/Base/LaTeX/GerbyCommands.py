# plasTeX/Base/LaTeX/GerbyCommands.py

from plasTeX import Command, Environment

class envsmallsize(Environment):
    """
    A custom LaTeX environment.
    """
    args = ''

class envfootnotesize(Environment):
    """
    A custom LaTeX environment.
    """
    args = ''

class envscriptsize(Environment):
    """
    A custom LaTeX environment.
    """
    args = ''

class envtinysize(Environment):
    """
    A custom LaTeX environment.
    """
    args = ''

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

class textiff(Command):
    """
    A custom LaTeX command \textiff.
    """
    args = ''

class itemstar(Command):
    """
    A custom LaTeX command \itemstar.
    """
    args = ''

class textdbend(Command):
    """
    A custom LaTeX command \textdbend.
    """
    args = ''

