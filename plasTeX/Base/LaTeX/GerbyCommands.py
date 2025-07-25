# plasTeX/Base/LaTeX/GerbyCommands.py

from plasTeX import Command, Environment
from plasTeX.Base.LaTeX.Math import EqnarrayStar
from plasTeX.Base.LaTeX.Arrays import Array

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

class envwebgif(Environment):
    """
    A custom LaTeX environment.
    """
    args = ''

class palign(Array):
    """
    A custom environment for aligning equations with tags on the right.
    It digests its content into a structured list of rows and cells.
    """
    pass

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

class ptag(Command):
    """
    A simple command \ptag{...} that just holds its content.
    It will be used as a delimiter inside the palign environment.
    """
    args = 'self'

class webgif(Command):
    """
    A simple command \webgif{...} that just holds its content.
    """
    args = 'self'

class audio(Command):
    """
    A simple command \webgif{...} that just holds its content.
    """
    args = 'self'

class warningsign(Command):
    """
    A custom LaTeX command \warningsign.
    """
    args = ''

class IPA(Command):
    """
    A custom LaTeX command \IPA.
    """
    args = 'self'

class doubleepigraph(Command):
    """
    A custom LaTeX command \doubleepigraph.
    """
    args = 'epigraph_one author_one epigraph_two author_two'

class xspace(Command):
    r"""
    A placeholder node for the \xspace command.
    The rendering logic is handled by the template.
    """
    # \xspace takes no arguments.
    args = ''
