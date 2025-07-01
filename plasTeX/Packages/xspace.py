"""
This package provides an implementation of the LaTeX xspace package.
"""

from plasTeX import Command
from plasTeX.Tokenizer import Token, BeginGroup, Space, Other, EscapeSequence
from plasTeX.Logging import getLogger

log = getLogger()

class xspace(Command):
    """
    The \xspace command.

    This command intelligently adds a space after a macro unless it is
    followed by certain punctuation or other commands that would make a
    space undesirable.
    """
    # This set will be populated by ProcessOptions with default exceptions.
    # It is a class attribute so it can be modified by user commands.
    _exceptions = set()

    def invoke(self, tex):
        """
        The invoke method for \xspace. This method contains the logic for
        intelligently inserting a space by peeking at the following tokens.
        """
        return self._peek_and_decide(tex, max_depth=10)

    def _peek_and_decide(self, tex, max_depth):
        """
        Peek at the next token and decide whether to insert a space.
        This method can recurse to handle expandable tokens.
        """
        if max_depth <= 0:
            # Recursion limit reached, assume space is needed to be safe.
            log.warning('xspace recursion limit reached. Adding a space.')
            return [self.ownerDocument.createTextNode(' '),
                    self.ownerDocument.createElement('@xspace@hook')]

        # Peek at next non-space token
        next_tok = None
        spaces = tex.readOptionalSpaces()
        try:
            # We use a new iterator so we don't consume from the main one
            it = tex.itertokens()
            next_tok = next(it)
            # Push it back so it's available for the main loop
            tex.pushToken(next_tok)
        except StopIteration:
            # End of stream, add a space.
            if spaces:
                tex.pushTokens(list(reversed(spaces)))
            return [self.ownerDocument.createTextNode(' ')]
        
        # We peeked, now push the spaces back on the stack to preserve them
        if spaces:
            tex.pushTokens(list(reversed(spaces)))

        # Now, `next_tok` is the token we're interested in, but it's still on the stream.
        
        # 1. Is it a letter? Add a space.
        if next_tok.catcode == Token.CC_LETTER:
            return [self.ownerDocument.createTextNode(' '),
                    self.ownerDocument.createElement('@xspace@hook')]

        # Suppression with {} or \ (control space)
        if isinstance(next_tok, BeginGroup) or \
           (hasattr(next_tok, 'nodeName') and next_tok.nodeName == ' '):
            return [self.ownerDocument.createElement('@xspace@hook')]

        # 2. Is it in the exception list?
        tok_name = ''
        if hasattr(next_tok, 'macroName') and next_tok.macroName:
            tok_name = next_tok.macroName
        else:
            tok_name = str(next_tok)
        
        # Also check for characters in the exception list
        if isinstance(next_tok, Other) and str(next_tok) in self.__class__._exceptions:
            return [self.ownerDocument.createElement('@xspace@hook')]

        if tok_name in self.__class__._exceptions:
            return [self.ownerDocument.createElement('@xspace@hook')]

        # 3. Is it expandable?
        if isinstance(next_tok, EscapeSequence):
            # Consume the token we just peeked at
            _ = next(tex.itertokens()) 
            
            # Expand it
            obj = self.ownerDocument.createElement(next_tok.macroName)
            obj.contextDepth = next_tok.contextDepth
            obj.parentNode = next_tok.parentNode
            expanded = obj.invoke(tex)
            if expanded is None:
                expanded = [obj]
            
            # Put the expansion back on the stream and recurse
            tex.pushTokens(expanded)
            return self._peek_and_decide(tex, max_depth - 1)
            
        # 4. Not a letter, not an exception, not expandable. Assume no space needed.
        # This covers cases like punctuation characters that are not in the exception list
        # but for which a space is generally not desired. This is a slight deviation
        # from TeX's xspace for practicality in plasTeX's parsing model.
        return [self.ownerDocument.createElement('@xspace@hook')]

class xspaceaddexceptions(Command):
    """ The \xspaceaddexceptions command """
    args = 'tokens:nox'

    def invoke(self, tex):
        self.parse(tex)
        tokens_to_add = self.attributes['tokens']
        for tok in tokens_to_add:
            if tok.catcode == Token.CC_SPACE:
                continue
            name = ''
            if hasattr(tok, 'macroName') and tok.macroName:
                name = tok.macroName
            else:
                name = str(tok)
            if name:
                xspace._exceptions.add(name)
        return []

class xspaceremoveexception(Command):
    """ The \xspaceremoveexception command """
    args = 'token:Tok'

    def invoke(self, tex):
        self.parse(tex)
        token_to_remove = self.attributes['token']
        
        name = ''
        if hasattr(token_to_remove, 'macroName') and token_to_remove.macroName:
            name = token_to_remove.macroName
        else:
            name = str(token_to_remove)

        if name and name in xspace._exceptions:
            xspace._exceptions.remove(name)
        return []

class _xspace_hook(Command):
    """ The \@xspace@hook command, does nothing by default """
    macroName = '@xspace@hook'
    def invoke(self, tex):
        return []

def ProcessOptions(options, document):
    """
    Called when the package is loaded.
    This sets up the initial state for the xspace package.
    """
    # Default exceptions from xspace.sty: 
    # \def\@xspace@exceptions@tlp{,.'/?;:!~`)\ \/\bgroup\egroup\@sptoken\space\@xobeysp\footnote\footnotemark}
    exceptions = {
        # Punctuation
        ',', '.', "'", '/', '?', ';', ':', '!', '~', '`', ')',
        # Commands
        ' ',          # control space \
        '/',          # \/ (italic correction)
        'bgroup',     # \bgroup
        'egroup',     # \egroup
        '@sptoken',
        'space',      # \space
        '@xobeysp',
        'footnote',
        'footnotemark',
        'relax',      # \relax should not be followed by a space
    }

    # Add exceptions for babel support, as mentioned in xspace documentation.
    babel_exceptions = {';', ':', '?', '!', ',', "'", '-'}
    exceptions.update(babel_exceptions)

    xspace._exceptions.update(exceptions)
    
    # Define the hook command
    document.context.addGlobal('@xspace@hook', _xspace_hook)
