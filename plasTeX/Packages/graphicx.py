#!/usr/bin/env python

import os, re
from plasTeX import Command

from plasTeX.Packages.graphics import DeclareGraphicsExtensions, graphicspath

class includegraphics(Command):
    args = '* [ options:dict ] file:str'
    packageName = 'graphicx'
    captionable = True

    def invoke(self, tex):
        res = Command.invoke(self, tex)

        f = self.attributes['file']

        if f:
            # Extract just the filename
            filename = os.path.basename(f) # This gives 'hundar.pdf'

            # Construct the final desired path for the web server
            final_path = f'/static/images/{filename}'

            # Store this path in a new attribute on the node.
            # The renderer will use this attribute.
            self.final_src = final_path

            # IMPORTANT: Nullify imageoverride to prevent plasTeX
            # from trying to copy or process the original file path.
            self.imageoverride = None

        return res

class DeclareGraphicsExtensions(DeclareGraphicsExtensions):
    packageName = 'graphicx'

class graphicspath(graphicspath):
    packageName = 'graphicx'
