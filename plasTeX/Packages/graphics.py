import os
from plasTeX import Command

class includegraphics(Command):
    args = '* [ ll ] [ ur ] file:str'
    packageName = 'graphics'
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

class graphicspath(Command):
    args = 'paths'
    packageName = 'graphics'
    def invoke(self, tex):
        res = Command.invoke(self, tex)
        output = [x.textContent.strip() for x in self.attributes['paths']]
        output = [x for x in output if x]
        self.ownerDocument.userdata.setPath(
                'packages/%s/paths' % self.packageName, output)
        return res

class DeclareGraphicsExtensions(Command):
    packageName = 'graphics'
    args = 'ext:list'
    def invoke(self, tex):
        res = Command.invoke(self, tex)
        ext = [x for x in self.attributes['ext'] if x]
        self.ownerDocument.userdata.setPath(
                'packages/%s/extensions' % self.packageName, ext)
        return res

class rotatebox(Command):
    args = 'angle:float self'

class scalebox(Command):
    args = 'hscale:float [ vscale:float ] self'

class reflectbox(Command):
    args = 'self'

class resizebox(Command):
    args = 'hlength:dimen vlength:dimen self'
