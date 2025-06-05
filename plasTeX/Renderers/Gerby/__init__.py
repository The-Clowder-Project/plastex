#!/usr/bin/env python

"""
How to test this (for now):
  0) get yourself a copy of the Stacks project repository
  1) put the tags/tags file in the tags/tmp folder (which is populated after running make tags)
  2) comment out all but one reasonably sized chapter in book.tex
  3) run plastex --renderer=Gerby book.tex in tags/tmp
"""

import os, re, shutil
import plasTeX
from plasTeX.Renderers.PageTemplate import Renderer as _Renderer
from plasTeX.Renderers import Renderable, mixin, unmix
from plasTeX.DOM import Node, Text as DOMText # Explicitly import Text
from plasTeX import Base
import json

log = plasTeX.Logging.getLogger()
gerby_log = plasTeX.Logging.getLogger('GerbyRenderer')
gerby_log.setLevel(plasTeX.Logging.DEBUG) # Ensure Gerby debug messages are shown

def simple_bib_parser(bib_file_path):
    """
    A very simple .bib file parser.
    Returns a dictionary mapping bib_keys to dictionaries of fields.
    Handles basic entries, comments, and multi-line fields.
    Does NOT handle @string macros, crossrefs well, or complex LaTeX in fields.
    """
    parsed_entries = {}
    if not os.path.exists(bib_file_path):
        gerby_log.warning(f"Simple Bib Parser: Bib file not found at {bib_file_path}")
        return parsed_entries

    try:
        with open(bib_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        gerby_log.error(f"Simple Bib Parser: Error reading bib file {bib_file_path}: {e}")
        return parsed_entries

    # Remove % comments, but be careful not to remove \%
    content_lines = []
    for line in content.splitlines():
        if line.strip().startswith('%') and not line.strip().startswith(r'\%'):
            continue
        content_lines.append(line)
    content = "\n".join(content_lines)

    # Regex to find entries: @type{key, fields... }
    entry_pattern = re.compile(r'@(\w+)\s*\{\s*([^,]+)\s*,(.*?)^\}', re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    for match in entry_pattern.finditer(content):
        bib_key = match.group(2).strip()
        fields_str = match.group(3)
        current_entry = {}
        
        # Split fields carefully, respecting brace and quote balancing
        raw_fields = []
        buffer = ""
        brace_level = 0
        in_quotes = False
        for char_idx, char in enumerate(fields_str):
            if char == '"' and (char_idx == 0 or fields_str[char_idx-1] != '\\'):
                if brace_level == 0 : 
                    in_quotes = not in_quotes
            elif not in_quotes: 
                if char == '{':
                    brace_level += 1
                elif char == '}':
                    brace_level -= 1
            
            if char == ',' and brace_level == 0 and not in_quotes:
                raw_fields.append(buffer.strip())
                buffer = ""
            else:
                buffer += char
        
        if buffer.strip():
            raw_fields.append(buffer.strip())

        for raw_field in raw_fields:
            parts = raw_field.split('=', 1)
            if len(parts) == 2:
                field_name = parts[0].lower().strip()
                field_value_raw = parts[1].strip()
                
                field_value_processed = field_value_raw
                if (field_value_raw.startswith('{') and field_value_raw.endswith('}')):
                    field_value_processed = field_value_raw[1:-1]
                elif (field_value_raw.startswith('"') and field_value_raw.endswith('"')):
                    field_value_processed = field_value_raw[1:-1]
                elif field_value_raw.isdigit() or (field_value_raw.isalpha() and field_value_raw.isupper()):
                     pass 


                temp_value_parts = []
                last_end = 0
                math_pattern = re.compile(r'(\\\$|\$\$[^\$]*?\$\$|\$(?!\$)[^\$]*?\$|\{\s*\$([^\$]*?)\$\s*\})')

                for math_match in math_pattern.finditer(field_value_processed):
                    temp_value_parts.append(field_value_processed[last_end:math_match.start()])
                    
                    matched_string = math_match.group(1)
                    
                    if matched_string == r'\$':
                        temp_value_parts.append('$') 
                    elif matched_string.startswith('$$') and matched_string.endswith('$$'):
                        temp_value_parts.append(f"\\[{matched_string[2:-2].strip()}\\]") 
                    elif matched_string.startswith('{$') and matched_string.endswith('$}'):
                        inner_math = math_match.group(2) 
                        temp_value_parts.append(f"${inner_math.strip()}$")
                    elif matched_string.startswith('$') and matched_string.endswith('$'):
                        temp_value_parts.append(f"${matched_string[1:-1].strip()}$") 
                    else: 
                        temp_value_parts.append(matched_string)
                    last_end = math_match.end()
                
                temp_value_parts.append(field_value_processed[last_end:])
                field_value_processed = "".join(temp_value_parts)
                
                for tex_cmd in ['emph', 'textit', 'textbf', 'texttt', 'textsl', 'textsc', 'textrm', 'textnormal']:
                    field_value_processed = re.sub(r'\\%s\s*\{(.*?)\}' % tex_cmd, r'\1', field_value_processed)
                field_value_processed = re.sub(r'\\[a-zA-Z@]+(?!\w)', '', field_value_processed) 
                
                current_entry[field_name] = field_value_processed.strip()
        
        if bib_key:
            parsed_entries[bib_key] = current_entry

    if not parsed_entries:
        gerby_log.warning(f"Simple Bib Parser: No entries parsed from {bib_file_path}. Check file content and parser logic.")
    return parsed_entries

def _format_authors_gerby(author_string):
    """
    Formats author string according to Gerby rules:
    - 1 author: Full surname
    - 2 authors: Initials of surnames (e.g., BS)
    - 3+ authors: Initials of surnames (e.g., AESV)
    - Group authors (e.g., {{nLab Authors}}): Full group name
    - Handles \href (takes the text part)
    """
    if not author_string:
        return "Unknown Author"

    # Handle group authors first
    group_match = re.match(r'^\{\{(.+)\}\}$', author_string.strip())
    if group_match:
        return group_match.group(1).strip()
    if author_string == "{Proof Wiki Contributors}":
        return "Proof Wiki Contributors"
    if author_string == "{nLab Authors}":
        return "nLab Authors"
    if author_string == "{Wikipedia Contributors}":
        return "Wikipedia Contributors"

    authors_list = []
    # Split by ' and '
    raw_authors = author_string.split(' and ')
    for raw_author in raw_authors:
        raw_author = raw_author.strip()
        # Handle \href{...}{Display Name}
        href_match = re.match(r'\\href\{.*\}\{(.+)\}', raw_author)
        if href_match:
            name_part = href_match.group(1).strip()
        else:
            name_part = raw_author

        # Remove any remaining TeX commands like \url or simple font commands
        name_part = re.sub(r'\\[a-zA-Z@]+(?:\{[^}]*\})?', '', name_part).strip()
        # Remove leftover braces if any (be conservative)
        if name_part.startswith('{') and name_part.endswith('}'):
            name_part = name_part[1:-1]
        
        name_part = name_part.strip()
        if not name_part: continue


        parts = name_part.split(',')
        if len(parts) > 1:  # "Last, First Middle"
            surname = parts[0].strip()
        else:  # "First Middle Last" or just "Last"
            name_words = name_part.split()
            if name_words:
                surname = name_words[-1].strip()
            else:
                continue # Skip empty name parts
        
        # A simple check for "van der" like prefixes which are part of surname
        if len(surname.split()) > 1 and any(p.islower() for p in surname.split()[:-1]):
             pass # Looks like a multi-word surname, keep it as is
        elif len(name_part.split()) > 1 and name_part.split()[-2].islower() and len(name_part.split()[-2]) > 1: # e.g. Peter van der Loo
            # Attempt to catch "van Last" type surnames
            surname_candidate = " ".join(name_part.split()[-2:])
            if name_part.split()[-2].islower(): # good chance it's part of the surname
                 surname = surname_candidate


        # Remove any remaining non-alphanumeric characters from the start for initial
        # For initial, take first char of first word of surname
        first_char_surname = ''.join(filter(str.isalnum, surname.split()[0]))
        if first_char_surname:
            authors_list.append({'full': name_part, 'surname': surname, 'initial': first_char_surname[0].upper()})
        elif surname : # if alphanumeric filter removed everything but surname was non-empty
            authors_list.append({'full': name_part, 'surname': surname, 'initial': 'X'}) # Fallback initial

    if not authors_list:
        return "Unknown Author"

    if len(authors_list) == 1:
        return authors_list[0]['surname']
    elif len(authors_list) >= 2 : # For 2 or more, use initials
        return "".join(author['initial'] for author in authors_list)
    
    return "Error Formatting Authors" # Should not be reached

# give the closest theorem environment to a node
def searchPrecedingTheorem(linear, node):
  # last visited node
  last = None

  for current in linear:
    # iterate over the theorems
    if current.nodeName == "thmenv":
      last = current

    # if the node matches, then return the last visited theorem node
    if current.isSameNode(node):
      return last.id

def willItBeWhitespace(node):
  if node.isElementContentWhitespace:
  # Spaces, newlines, and comments are whitespace known to plasTeX
    return True
  elif node.nodeName in ["label","reference","slogan","history"]:
  # labels, references, slogans, and history are currently assumed to be whitespace
    return True
  elif node.nodeName == "par":
  # A paragraph is whitespace if all it contains is whitespace
    return all([willItBeWhitespace(child) for child in node.childNodes])

class GerbyRenderable(Renderable):
  @property
  def filenameoverride(self):
    # handle tags
    if "tag" in self.userdata:
      environment = self.nodeName
      if self.nodeName == "thmenv":
        environment = self.thmName

        # decide whether or not paragraphs are whitespace
        for child in self.childNodes:
          child.isItWhitespace = willItBeWhitespace(child)

      return environment + "-" + self.ref + "-" + self.userdata["tag"] + "-" + self.id + ".tag"

    # handle proofs
    if self.nodeName == "proof":
      # caption can contain a \ref
      if "caption" in self.attributes and self.attributes["caption"] and len(self.attributes["caption"].getElementsByTagName("ref")) > 0:
        # use the first one for now, in theory there could be more
        label = [ref.attributes["label"] for ref in self.attributes["caption"].getElementsByTagName("ref")][0]
      # just take the closest theorem
      else:
        label = searchPrecedingTheorem(self.ownerDocument.userdata["linear"], self)

      if label in self.ownerDocument.userdata["labels"]:
        tag = self.ownerDocument.userdata["labels"][label]
        self.ownerDocument.userdata["proofs"][tag] += 1
        return tag + "-" + str(self.ownerDocument.userdata["proofs"][tag]) + ".proof"

    # handle slogans, history, ...
    if self.nodeName in ["history", "slogan", "reference"]:
      # Reach top level environment containing this node.
      # ASSUMPTION: The only other node type possibly containing this node is
      #             a paragraph node.
      parentEnv = self.parentNode
      while parentEnv.nodeName == "par":
        parentEnv = parentEnv.parentNode
      label = parentEnv.id

      if label in self.ownerDocument.userdata["labels"]:
        tag = self.ownerDocument.userdata["labels"][label]
        return tag + "." + self.nodeName

    raise AttributeError

  @property
  def local_footnotes(self):
      if hasattr(self, '_local_footnotes_cache'):
          return self._local_footnotes_cache
      footnotes_collected = []
      nodes_to_visit_queue = list(getattr(self, 'childNodes', []))
      head = 0
      while head < len(nodes_to_visit_queue):
          current_node = nodes_to_visit_queue[head]; head += 1
          if current_node.nodeName == 'footnote':
              current_node.userdata['local_number'] = len(footnotes_collected) + 1
              footnotes_collected.append(current_node)
          if hasattr(current_node, 'childNodes') and current_node.childNodes:
              nodes_to_visit_queue[head:head] = current_node.childNodes
      self._local_footnotes_cache = footnotes_collected
      return footnotes_collected

  def _get_flat_renderable_nodes_dfs(self, start_node):
      flat_list = []
      nodes_to_visit_stack = list(reversed(list(getattr(start_node, 'childNodes', []))))
      while nodes_to_visit_stack:
          current_node = nodes_to_visit_stack.pop()
          if current_node.nodeName == 'footnote' or isinstance(current_node, DOMText):
              flat_list.append(current_node)
          elif current_node.blockType and current_node.nodeName not in ['footnote', '#text']:
              flat_list.append(None) 
              if hasattr(current_node, 'childNodes') and current_node.childNodes:
                  for child_node in reversed(current_node.childNodes): nodes_to_visit_stack.append(child_node)
              flat_list.append(None) 
          elif hasattr(current_node, 'childNodes') and current_node.childNodes:
              for child_node in reversed(current_node.childNodes): nodes_to_visit_stack.append(child_node)
          elif not (hasattr(current_node, 'isElementContentWhitespace') and current_node.isElementContentWhitespace):
              flat_list.append(None) 
      return flat_list

  def preprocess_footnotes_for_compression(self):
      all_footnotes_in_this_scope = self.local_footnotes
      if not all_footnotes_in_this_scope: return
      for fn_node in all_footnotes_in_this_scope:
          fn_node.userdata['suppress_inline_mark'] = False
          fn_node.userdata['compressed_mark_text'] = None
      flat_renderable_nodes = self._get_flat_renderable_nodes_dfs(self)
      active_footnote_sequence = []
      for node in flat_renderable_nodes:
          if node is None: 
              if len(active_footnote_sequence) > 1:
                  active_footnote_sequence[0].userdata['compressed_mark_text'] = ",".join(str(fn.userdata['local_number']) for fn in active_footnote_sequence)
                  for k_fn in active_footnote_sequence[1:]: k_fn.userdata['suppress_inline_mark'] = True
              active_footnote_sequence = []
              continue
          is_footnote = (node.nodeName == 'footnote')
          is_ignorable_whitespace = (isinstance(node, DOMText) and not node.strip())
          if is_footnote:
              if 'local_number' not in node.userdata: 
                  if active_footnote_sequence:
                      if len(active_footnote_sequence) > 1:
                          active_footnote_sequence[0].userdata['compressed_mark_text'] = ",".join(str(fn.userdata['local_number']) for fn in active_footnote_sequence)
                          for k_fn in active_footnote_sequence[1:]: k_fn.userdata['suppress_inline_mark'] = True
                      active_footnote_sequence = []
                  continue
              active_footnote_sequence.append(node)
          elif not is_ignorable_whitespace:
              if len(active_footnote_sequence) > 1:
                  active_footnote_sequence[0].userdata['compressed_mark_text'] = ",".join(str(fn.userdata['local_number']) for fn in active_footnote_sequence)
                  for k_fn in active_footnote_sequence[1:]: k_fn.userdata['suppress_inline_mark'] = True
              active_footnote_sequence = []
      if len(active_footnote_sequence) > 1:
          active_footnote_sequence[0].userdata['compressed_mark_text'] = ",".join(str(fn.userdata['local_number']) for fn in active_footnote_sequence)
          for k_fn in active_footnote_sequence[1:]: k_fn.userdata['suppress_inline_mark'] = True

  def get_formatted_bibitem_link_text(self, bib_key):
      doc = self.ownerDocument
      
      # Use directly parsed bib data as the primary source
      direct_bib_data = doc.userdata.get('_direct_bib_data', {})
      direct_entry = direct_bib_data.get(bib_key)

      if direct_entry:
          # gerby_log.debug(f"GFBLT: Found key '{bib_key}' in _direct_bib_data.")
          author_field_value = direct_entry.get('author', "Unknown Author")
          author_text = _format_authors_gerby(author_field_value)
              
          title_text = direct_entry.get('title', bib_key)
          # gerby_log.debug(f"GFBLT: (Direct Parse) For key '{bib_key}', Author: '{author_text}', Title: '{title_text}'")
          return f"{author_text}, {title_text}"

      # Fallback to standard plasTeX bibitem storage (populated from .bbl, if any)
      bibitems_dict = doc.userdata.getPath('bibliography/bibitems', {})
      bibitem_node = bibitems_dict.get(bib_key)
      
      bibcites_dict = doc.userdata.getPath('bibliography/bibcites', {})
      cite_info_node = bibcites_dict.get(bib_key)

      if not bibitem_node:
          gerby_log.warning(f"GFBLT: bibitem_node for key '{bib_key}' NOT found in userdata['bibliography/bibitems'] "
                            f"AND not in _direct_bib_data. This means the bib file might be missing or the key is incorrect. "
                            f"Available bibitem keys (from .bbl): {list(bibitems_dict.keys())}")
          return f"[Unknown Reference: {bib_key}]"
      
      # gerby_log.debug(f"GFBLT: bibitem_node for key '{bib_key}' found in standard userdata (from .bbl).")
      author_text = "Unknown Author" # Default if not found below
      if cite_info_node and hasattr(cite_info_node, 'attributes') and \
         'author' in cite_info_node.attributes:
          author_frag = cite_info_node.attributes['author']
          if author_frag:
              author_text_candidate = (author_frag.textContent if hasattr(author_frag, 'textContent') else str(author_frag)).strip()
              if author_text_candidate: author_text = _format_authors_gerby(author_text_candidate)
      elif hasattr(bibitem_node, 'attributes') and 'author' in bibitem_node.attributes: 
          author_frag = bibitem_node.attributes['author']
          if author_frag:
              author_text_candidate = (author_frag.textContent if hasattr(author_frag, 'textContent') else str(author_frag)).strip()
              if author_text_candidate: author_text = _format_authors_gerby(author_text_candidate)
      elif hasattr(bibitem_node, 'textContent'): 
          # This heuristic for author from raw textContent is less reliable for structured formatting
          content = bibitem_node.textContent.strip()
          year_match = re.search(r'\(\s*\d{4}\s*\)\.?|\b\d{4}\b\.?', content)
          title_delimiter_match = re.search(r'\.\s+(?=[A-Z"\'`\u2018\u201C])|:\s+|“|‘|\s+\\emph{|\\textit{', content)
          end_author_pos = -1
          if year_match: end_author_pos = year_match.start()
          if title_delimiter_match:
              if end_author_pos == -1 or title_delimiter_match.start() < end_author_pos:
                  end_author_pos = title_delimiter_match.start()
          if end_author_pos > 0 :
              author_text_candidate = content[:end_author_pos].strip(' .,;:?!')
              if author_text_candidate: author_text = _format_authors_gerby(author_text_candidate)
          # If still "Unknown Author", and we have content, pass the content to the formatter
          elif author_text == "Unknown Author" and content:
              author_text = _format_authors_gerby(content.split('.')[0]) # Very rough guess

      title_text = bib_key 
      if hasattr(bibitem_node, 'attributes') and 'title' in bibitem_node.attributes:
          title_frag = bibitem_node.attributes['title']
          if title_frag:
              title_text = (title_frag.textContent if hasattr(title_frag, 'textContent') else str(title_frag)).strip()
      else:
          if hasattr(bibitem_node, 'getElementsByTagName'):
              emph_nodes = bibitem_node.getElementsByTagName('emph')
              if not emph_nodes: emph_nodes = bibitem_node.getElementsByTagName('textit')
              if emph_nodes and hasattr(emph_nodes[0], 'textContent'):
                  extracted_title = emph_nodes[0].textContent.strip()
                  if extracted_title and extracted_title[-1] in ['.', ',']:
                      extracted_title = extracted_title[:-1].strip()
                  if extracted_title: title_text = extracted_title
      
      gerby_log.debug(f"GFBLT: (Userdata/BBL Parse) For key '{bib_key}', Author: '{author_text}', Title: '{title_text}'")
      return f"{author_text}, {title_text}"


"""Helper functors for Gerby"""

def decorateTags(node, labels):
  """Recursively decorate labeled nodes with Gerby-specific userdata"""
  if node.nodeType == plasTeX.Macro.ELEMENT_NODE and node.id[0:2] != "a0":
    # plasTeX.Packages.hyperref parses hypertargets, but we ignore them
    if node.nodeName != "hypertarget" and node.id in labels:
      node.userdata["tag"] = labels[node.id]

      if node.nodeName not in ["part", "chapter", "section", "subsection", "subsubsection"]:
        node.userdata["propagate"] = True

  if node.nodeName == "proof":
    node.userdata["propagate"] = True

    # make sure that there is always a paragraph in a proof
    if not all([child.nodeName == "par" for child in node.childNodes]):
      node.paragraphs()

  for child in node.childNodes:
    decorateTags(child, labels)

def loadTags(document):
  """Read the tags file and construct the tags and labels dictionary"""
  tags_file_path = os.path.join(document.userdata["working-dir"], document.config["gerby"]["tags"])
  if not os.path.exists(tags_file_path):
    gerby_log.error(f"Tags file not found: {tags_file_path}")
    document.userdata["tags"] = {}
    document.userdata["labels"] = {}
    document.userdata["proofs"] = {}
    return

  with open(tags_file_path) as f:
    content = f.readlines()

  document.userdata["tags"] = dict()   # tag to label
  document.userdata["labels"] = dict() # label to tag
  document.userdata["proofs"] = dict() # count number of proofs for a tag

  for line in content:
    if line[0] == "#": continue
    try:
        (tag, label) = line.rstrip().split(",")
        document.userdata["tags"][tag] = label
        document.userdata["labels"][label] = tag
        document.userdata["proofs"][tag] = 0
    except ValueError:
        gerby_log.warning(f"Malformed line in tags file: {line.rstrip()}")


def linearRepresentation(document):
  """Make a linear representation of the document containing theorems and proofs"""
  document.userdata["linear"] = list()
  stack = list()

  stack.extend(document.childNodes)

  while len(stack) > 0:
    node = stack.pop()

    if node.nodeName in ["thmenv", "proof", "reference", "history", "slogan"]:
      document.userdata["linear"].append(node)

    stack.extend(node.childNodes)

  document.userdata["linear"] = list(reversed(document.userdata["linear"]))

def tagRollCall(document):
    # Check whether or not all tags appear in the document
    attendanceSheet = dict(map(lambda t: (t, False), document.userdata.get("tags", {}).keys()))

    stack = list()
    stack.extend(document.childNodes)
    while len(stack) > 0:
        node = stack.pop()
        try:
            tag = node.userdata.get("tag")
            if tag and tag in attendanceSheet:
                attendanceSheet[tag] = True
        except:
            pass

        stack.extend(node.childNodes)
    return attendanceSheet

def partsList(document):
  """Make an association between parts and chapters"""
  parts = dict()
  stack = list()

  stack.extend(document.childNodes)
  current = None

  while len(stack) > 0:
    node = stack.pop()

    if node.nodeName == "part":
      current = node.ref.source
      parts[current] = list()
    elif node.nodeName == "chapter" and current != None:
      parts[current].append(node.ref.source)

    stack.extend(node.childNodes)

  return parts

def copyBibliographies(document):
  """Copy bibliography files by looking for bibliography elements"""
  bib_filenames_found = set()
  for node in document.getElementsByTagName('bibliography'):
      files_str = node.attributes.get("files")
      if files_str:
          for f_stem in files_str.split(","):
              bib_filenames_found.add(f_stem.strip() + ".bib")
  for node in document.getElementsByTagName('addbibresource'):
      if hasattr(node, 'attributes') and node.attributes.get('self') and \
         hasattr(node.attributes['self'], 'textContent'):
          bib_filename = node.attributes['self'].textContent.strip()
          if bib_filename:
              if not bib_filename.endswith('.bib'): bib_filename += '.bib'
              bib_filenames_found.add(bib_filename)
  gerby_log.debug(f"Found potential bibliography source files: {bib_filenames_found}")
  for bib_file_actual_name in bib_filenames_found:
      source_bib = os.path.join(document.userdata["working-dir"], bib_file_actual_name)
      if len(bib_filenames_found) == 1: # If only one, name it bibliography.bib for simple_bib_parser
          dest_bib_name_in_output = "bibliography.bib"
      else: # Otherwise, keep original name
          dest_bib_name_in_output = bib_file_actual_name
      dest_bib = os.path.join(os.getcwd(), dest_bib_name_in_output)
      if os.path.exists(source_bib):
          shutil.copyfile(source_bib, dest_bib)
          gerby_log.debug(f"Copied {source_bib} to {dest_bib}")
      else:
          gerby_log.warning(f"Bibliography file {source_bib} not found for copying.")


def checkLabels(document):
  stack = list()
  stack.extend(document.childNodes)

  while len(stack) > 0:
    node = stack.pop()

    if node.nodeName in ["thmenv", "chapter", "section", "subsection", "subsubsection"]:
      if node.id[0:3] == "a00" and hasattr(node.ref, "source"):
        print("%s %s does not have a label" % (node.thmName if node.nodeName == "thmenv" else node.nodeName, node.ref.source))

    stack.extend(node.childNodes)



class Gerby(_Renderer):
  """ Tag-aware renderer for HTML documents """

  fileExtension = ''
  imageTypes = ['.png','.jpg','.jpeg','.gif']
  vectorImageTypes = ['.svg']
  renderableClass = GerbyRenderable

  def loadTemplates(self, document):
    _Renderer.loadTemplates(self, document)
    rendererdata = document.rendererdata["gerby"] = dict()
    config = document.config
    config["files"]["split-level"] = -2
    rendererDir = os.path.dirname(__file__)
    srcDir = document.userdata['working-dir']
    buildDir = os.getcwd()
    for resrc in document.packageResources:
        resrc.alter(renderer=self, rendererName='gerby', document=document, target=buildDir)

  def cleanup(self, document, files, postProcess=None):
    res = _Renderer.cleanup(self, document, files, postProcess=postProcess)
    return res

  def processFileContent(self, document, s):
    s = _Renderer.processFileContent(self, document, s)
    for fun in document.rendererdata["gerby"].get('processFileContents', []):
      s = fun(document, s)
    s = re.compile(r'<p>\s*</p>', re.I).sub(r'', s)
    s = re.compile(r'<p>(<div class="equation".*?<\/div>)<\/p>', flags=re.DOTALL).sub(r'\1',s)
    return s

  def _ensure_bibliography_processed(self, document):
      if '_direct_bib_data' in document.userdata: return
      gerby_log.info("Attempting direct .bib parse as primary data source for Gerby.")
      
      bib_file_to_parse = None
      standard_bib_path = os.path.join(os.getcwd(), "bibliography.bib") # CWD is output dir
      if os.path.exists(standard_bib_path):
          bib_file_to_parse = standard_bib_path
      else: 
          potential_bib_files = [f for f in os.listdir(os.getcwd()) if f.endswith('.bib')]
          if potential_bib_files:
              bib_file_to_parse = os.path.join(os.getcwd(), potential_bib_files[0])
              if len(potential_bib_files) > 1:
                  gerby_log.warning(f"Multiple .bib files found in output directory: {potential_bib_files}. Parsing only {bib_file_to_parse} for _direct_bib_data.")
      
      if bib_file_to_parse:
          parsed_data = simple_bib_parser(bib_file_to_parse)
          document.userdata['_direct_bib_data'] = parsed_data
          gerby_log.info(f"Directly parsed {len(parsed_data)} entries from {bib_file_to_parse} into _direct_bib_data.")
      else:
          gerby_log.warning(f"No .bib file found in output directory for direct parsing by _ensure_bibliography_processed (expected e.g. bibliography.bib).")
          document.userdata['_direct_bib_data'] = {}


  def render(self, document):
    gerby_log.debug(f"Gerby.render() CALLED. Current CWD: {os.getcwd()}")
    gerby_log.debug(f"  Working-dir from userdata: {document.userdata.get('working-dir', 'Not Set')}")
    gerby_log.debug(f"  Jobname from userdata: {document.userdata.get('jobname', 'Not Set')}")
    bibitems_at_start = document.userdata.getPath('bibliography/bibitems', {})
    bibcites_at_start = document.userdata.getPath('bibliography/bibcites', {})
    gerby_log.debug(f"  BEFORE Gerby processing: userdata bibitems keys: {list(bibitems_at_start.keys())}")
    gerby_log.debug(f"  BEFORE Gerby processing: userdata bibcites keys: {list(bibcites_at_start.keys())}")

    loadTags(document)
    copyBibliographies(document) 
    self._ensure_bibliography_processed(document) 

    checkLabels(document)
    decorateTags(document, document.userdata.get("labels", {})) 
    linearRepresentation(document)

    tagAttendanceSheet = tagRollCall(document)
    for tag_key in filter(lambda t: not tagAttendanceSheet[t], tagAttendanceSheet):
      log.warning("document does not contain tag %s" % tag_key) 

    parts = partsList(document)
    with open("parts.json", "w") as f:
      json.dump(parts, f)
    
    gerby_log.debug(f"Gerby.render(): Just before _Renderer.render, userdata bibitems keys: {list(document.userdata.getPath('bibliography/bibitems', {}).keys())}")
    gerby_log.debug(f"Gerby.render(): Just before _Renderer.render, _direct_bib_data keys: {list(document.userdata.get('_direct_bib_data', {}).keys())}")

    _Renderer.render(self, document)

    if "footnotes" in document.userdata:
      mixin(Node, Gerby.renderableClass)
      Node.renderer = self
      for footnote in document.userdata["footnotes"]:
        with open("{0}.footnote".format(footnote.id),"w") as f:
          f.write(str(footnote))
      del Node.renderer
      unmix(Node, Gerby.renderableClass)

    with open("meta.statistics", "w") as f:
      json.dump(document.context.meta, f)

Renderer = Gerby


def outputTree(node, depth=0):
  if hasattr(node, "id") and node.id[0:2] != "a0":
    print("-" * depth + node.nodeName + ": " + node.id + ", level = " + str(depth))
  elif node.nodeName == "index":
    print("*" * depth + node.nodeName)
  else:
    print("-" * depth + node.nodeName)

  for child in node.childNodes:
    outputTree(child, depth + 1)
