#!/usr/bin/env python

import os, re
from plasTeX import Command

from plasTeX.Packages.graphics import DeclareGraphicsExtensions, graphicspath

class includegraphics(Command):
    args = '* [ options:dict ] file:str'
    packageName = 'graphicx'
    captionable = True

    def invoke(self, tex):
        # This parses the arguments like [width=...] and {file...}
        # into self.attributes
        res = Command.invoke(self, tex)

        f = self.attributes.get('file')
        if not f:
            return [] # No file, so render nothing

        # --- Your Custom Path Logic ---
        # 1. Get the base filename (e.g., "hundar.pdf")
        basename = os.path.basename(f)
        # 2. Get the filename and its extension
        filename_no_ext, ext = os.path.splitext(basename)

        # 3. Conditionally change the extension
        if ext.lower() == '.pdf':
            # If it's a PDF, change the extension to .svg
            final_filename = filename_no_ext + '.svg'
        else:
            # Otherwise, keep the original filename and extension
            final_filename = basename
        # 4. Store the final path in a new attribute for the template
        self.final_src = os.path.join('/static/images/', final_filename)
        # --- End Custom Path Logic ---

        # This tells plasTeX to NOT use the imager for this node.
        self.imageoverride = None

        # Optionally handle other arguments like width
        options = self.attributes.get('options', {})
        if options and 'width' in options:
            width_val = options['width']
            # The value could be `\linewidth`, which we can map to CSS
            if hasattr(width_val, 'source'):
                self.style['width'] = width_val.source.replace('\\linewidth', '100%')
            else:
                self.style['width'] = str(width_val)

        return res

class DeclareGraphicsExtensions(DeclareGraphicsExtensions):
    packageName = 'graphicx'

class graphicspath(graphicspath):
    packageName = 'graphicx'
