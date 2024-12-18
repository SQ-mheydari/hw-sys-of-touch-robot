"""
Auto-document generator for Python 3.
Some features:
- Uses API node structure that has been parsed fro Python code.
- Aims to work with reStructuredText formatting.
- Parse general description and arguments from class method docstring.
- PDF output.

The reason this module exists is that most / all HTML -> PDF converters produce bad quality especially with
tables. This implementation also allows better page layout control.
"""

from fpdf import FPDF, HTMLMixin
import os
from .parser import *
import logging

log = logging.getLogger(__name__)


class DocstringParser:
    """
    Parses some annotations from a docstring by assuming reStructuredText formatting.
    """

    def __init__(self, docstring, line_break='\n'):
        lines = docstring.splitlines()

        self.descr = ""
        self.parameters = {}
        self.returns = None
        self.example = None

        line_ix = 0
        state = "DEFAULT"
        state_param = ""
        add_line_break = False

        while line_ix < len(lines):
            line = lines[line_ix]
            line_ix += 1
            stripped_line = line.strip()

            try:
                if stripped_line.startswith(":"):
                    if stripped_line.startswith(":param"):
                        state = "PARAM"
                        parts = stripped_line[6:].split(":", 1)

                        text = parts[1]
                        state_param = parts[0].strip()
                        self.parameters[state_param] = text.strip()

                    elif stripped_line.startswith(":return"): # Can be ":return:" or ":returns:"
                        state = "RETURN"
                        parts = stripped_line.split(":", 2)

                        self.returns = parts[2].strip()
                    elif stripped_line.startswith(":example:"):
                        self.example = stripped_line[9:]

                        while line_ix < len(lines):
                            line = lines[line_ix]
                            stripped_line = line.strip()

                            if stripped_line.startswith(":"):
                                break
                            else:
                                line_ix += 1

                            self.example += line_break + stripped_line

                # If we have empty line and description exists, we'll add line break when appending next line of text
                elif len(stripped_line) == 0 and len(self.descr) != 0:
                    add_line_break = True

                else:
                    if state == "PARAM":
                        # We are in @param block and want to add a space and content of new line for the parameter description
                        self.parameters[state_param] += " " + stripped_line
                    elif state == "RETURN":
                        self.returns += " " + stripped_line
                    else:
                        # Add line break if previous line was empty and we are composing description
                        if add_line_break:
                            self.descr += line_break
                            add_line_break = False
                        self.descr += stripped_line + " "
                        state = "DEFAULT"
            except Exception as e:
                print("Error parsing line: " + line)
                raise e

        self.descr = self.descr.strip()

        if self.example:
            self.example = self.example.strip()


class PdfWriter(FPDF, HTMLMixin):
    """
    Utility class to write a PDF that has suitable formatting for API documentation.
    """

    def __init__(self):
        FPDF.__init__(self)
        HTMLMixin.__init__(self)

        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')

        # Enable getting total page count in footer.
        self.alias_nb_pages()

        self.text_area_width = (self.w - self.l_margin - self.r_margin)

        # Load custom font.
        self.add_font('Calibri', '', os.path.join(self.data_dir, 'calibri.ttf'), uni=True)
        self.add_font('Calibri', 'B', os.path.join(self.data_dir, 'calibrib.ttf'), uni=True)

        self.num_module_headers = 0
        self.num_class_headers = 0

        # Number of missing docstring parts.
        self.num_missing = 0

        # Set document margins.
        self.set_margins(10, 25, 10)

        # Define font names used by document.
        self.normal_font = "Calibri"
        self.monospace_font = "Courier"

        self.set_title("TnT Client Python Reference")
        self.set_subject("TnT Client Python Reference")
        self.set_author("OptoFidelity")
        self.set_creator("OptoFidelity")
        self.set_keywords("TnT, Client, Python, API")

    def add_title_page(self):
        self.add_page()
        self.image(os.path.join(self.data_dir, 'of_title.jpg'), x=self.l_margin, y=self.t_margin, w=self.text_area_width)
        self.set_text_color(0, 82, 148)
        self.set_font(self.normal_font, size=44)
        self.set_y(170)
        self.cell(0, 44, "OptoFidelity Touch and Test")
        self.set_text_color(0, 0, 0)
        self.set_font(self.normal_font, size=36)
        self.set_y(200)
        self.cell(0, 36, "Python Client Reference")

    def parse_markdown(self, filename):
        """
        Parses Markdown file and generates PDF page.
        N.B. Only supports a very limited Markdown syntax subset.
        """

        self.add_page()

        with open(filename) as file:
            data = file.read()

        lines = data.split('\n')

        monospace = False

        for line in lines:
            if line.startswith('#'):
                self.add_header(line[1:])
            elif line.startswith('```'):
                monospace = not monospace
                self.ln(5) # Some space around monospace text
            elif len(line) > 0:
                if monospace:
                    self.add_paragraph(line, font_name=self.monospace_font)
                else:
                    self.add_paragraph(line)

    def wrap_text(self, text, max_line_width):
        """
        Wrap given text according to maximum line width.
        :return: List of lines that obey maximum width.
        """

        lines = []
        words = text.split(' ')
        line = ""

        for w in words:

            if self.get_string_width(line + ' ' + w) < max_line_width:
                line += w + ' '
            else:
                lines.append(line)
                line = w + ' '

        lines.append(line)

        return lines

    def footer(self):
        """
        Define page footer.
        """

        # No footer in title page.
        if self.page_no() == 1:
            return

        # Page number.
        self.set_y(-10)
        self.set_font(self.normal_font, size=8)
        self.cell(0, 10, "Page " + str(self.page_no()) + " / {nb}", align='C')

        self.set_y(-self.b_margin)
        self.set_font(self.normal_font, size=10)
        self.set_text_color(255, 255, 255)

        w = (self.w - self.l_margin - self.r_margin) / 3

        # OptoFidelity footer block.
        self.set_fill_color(238, 49, 32)
        self.cell(w, 10, "COMPANY CONFIDENTIAL", fill=1, align="C")
        self.set_fill_color(102, 196, 48)
        self.cell(w, 10, "www.optofidelity.com", fill=1, align="C")
        self.set_fill_color(23, 111, 192)
        self.cell(w, 10, "sales@optofidelity.com", fill=1, align="C")

        self.set_fill_color(255, 255, 255)
        self.set_text_color(0, 0, 0)

    def header(self):
        """
        Define page header.
        """

        # No header in title page.
        if self.page_no() == 1:
            return

        # OptoFidelity logo.
        self.image(os.path.join(self.data_dir, 'of_logo.png'), x=5, y=5, w=40)

    def add_paragraph(self, text, font_name=None, indent=False):
        """
        Paragraph is just multi-line text.
        """

        if font_name is None:
            self.set_font(self.normal_font, size=10)
        else:
            self.set_font(font_name, size=10)

        x = self.get_x()

        if indent:
            self.set_x(x + 2.0)

        self.multi_cell(0, 5, text, border=0, align='L')
        self.set_x(x)

    def add_description(self, name, text):
        """
        Add description that consists of bold name and mono-space text.
        """

        self.set_font(self.normal_font, size=10, style='B')
        self.ln()
        self.cell(self.get_string_width(name), 5, name, border=0)

        if text is not None:
            self.set_font(self.monospace_font, size=10)
            self.set_fill_color(200, 200, 255)
            self.cell(self.get_string_width(text) + 3, 5, text, border=0, ln=1, fill=1)
            self.set_fill_color(255, 255, 255)
        else:
            self.ln()

    def determine_font_size(self, text, font_name, start_font_size, max_width):
        """
        Determine font size that makes given text fit to given maximum width.
        """
        font_size = start_font_size

        while font_size > 6:
            self.set_font(font_name, size=font_size)

            if self.get_string_width(text) <= max_width:
                return font_size

            font_size -= 1

    def add_row(self, text1, text2):
        """
        Add two-column table row. These can be added one after another to create an entire table.
        First column uses mono-space font and second column uses normal font.
        First column content must be single-line. Second column content can span multiple lines.
        Intended use-case is function parameter descriptions.
        """

        # Column widths obey the golden ratio.
        golden_ratio = 1.61803398875
        col_width1 = self.text_area_width / (golden_ratio + 1)
        col_width2 = self.text_area_width * golden_ratio / (golden_ratio + 1)
        col_height = 5

        lines = self.wrap_text(text2, col_width2)

        total_height = col_height * len(lines)

        # Position fiddling below only works if row does not break page.
        if self.h - self.b_margin - self.t_margin - self.get_y() - total_height <= 1:
            self.add_page()

        x = self.get_x()
        y = self.get_y()

        # Create column borders.
        self.cell(col_width1, total_height, "", border=1, ln=0)
        self.cell(col_width2, total_height, "", border=1, ln=0)

        self.set_x(x)
        self.set_y(y)

        # Column 1 text. Choose font so that text fits in column.
        font_size = self.determine_font_size(text1, self.monospace_font, 10, col_width1)
        self.set_font(self.monospace_font, size=font_size)
        self.cell(self.get_string_width(text1), col_height, text1, border=0, ln=1)

        self.set_y(y)

        self.set_font(self.normal_font, size=10)

        # Column 2 text.
        for line in lines:
            self.set_x(x + col_width1)
            self.cell(self.get_string_width(line), col_height, line, border=0, ln=1)

    def add_header(self, text):
        """
        Add big generic header.
        """

        self.num_module_headers += 1
        text_size = 14

        prefixed_text = str(self.num_module_headers) + text

        self.set_font(self.normal_font, style='B', size=text_size)
        self.cell(self.get_string_width(prefixed_text), text_size, prefixed_text, border=0, ln=1)

    def add_module_header(self, text):
        """
        Add big header for module documentation.
        """

        # Each module starts new page.
        self.add_page()

        self.num_module_headers += 1
        self.num_class_headers = 0
        text_size = 14

        prefix = str(self.num_module_headers) + " Module: "

        self.set_font(self.normal_font, style='B', size=text_size)
        self.cell(self.get_string_width(prefix), text_size, prefix, border=0)
        self.set_font(self.monospace_font, size=text_size)
        self.cell(self.get_string_width(text), text_size, text, border=0, ln=1)

    def add_class_header(self, text):
        """
        Add small header for class documentation.
        """

        self.num_class_headers += 1
        text_size = 12

        prefix = str(self.num_module_headers) + "." + str(self.num_class_headers) + " Class: "

        self.set_font(self.normal_font, style='B', size=text_size)
        self.cell(self.get_string_width(prefix), text_size, prefix, border=0)
        self.set_font(self.monospace_font, size=text_size)
        self.cell(self.get_string_width(text), text_size, text, border=0, ln=1)


def write_api_method(writer, method : ApiMethod, node_name):
    """
    Write document for API method.
    :param writer: Writer object.
    :param method: ApiMethod object.
    """

    writer.add_description("Method:  ", method.client_name)

    writer.add_paragraph("Description:")

    doc = method.doc

    # Function general description.
    if doc is None or len(doc.strip()) == 0:
        writer.num_missing += 1

        # Can't continue if there is no docstring
        raise Exception("Method '{}' has not docstring in '{}'!".format(method.name, node_name))

    parser = DocstringParser(doc)

    writer.add_paragraph(parser.descr, indent=True)

    writer.add_paragraph("Arguments:")

    # Function parameters
    if len(method.parameters) == 0:
        # There are no parameters except "self".
        writer.add_paragraph("None", indent=True)
    else:
        for p in method.parameters:
            # Check if parameter is mentioned in parsed docstring.
            if p.name in parser.parameters and len(parser.parameters[p.name].strip()) > 0:
                writer.add_row(p.name, parser.parameters[p.name])
            else:
                raise Exception("Parameter '{}' of method '{}' has no entry in docstring in '{}'!"
                                .format(p.name, method.name, node_name))

    # Function return value
    if parser.returns is not None:
        writer.add_paragraph("Returns:")

        if len(parser.returns.strip()) == 0:
            raise Exception("Return value of method '{}' has no entry in docstring in '{}'!"
                            .format(method.name, node_name))
        else:
            writer.add_paragraph(parser.returns, indent=True)

    # Example
    if parser.example is not None:
        writer.add_paragraph("Example:")
        writer.add_paragraph(parser.example, indent=True)

        writer.ln(5)


def write_api_property(writer, prop : ApiProperty, node_name):
    """
    Write document for API property.
    :param writer: Writer object.
    :param prop: ApiProperty object.
    """

    if prop.doc is None or len(prop.doc.strip())==0:
        raise Exception("Property '{}' has no docstring in '{}'!".format(prop.name, node_name))
    else:
        parser = DocstringParser(prop.doc)

        writer.add_row(prop.name, parser.descr)


def write_api_node(writer, api_node : ApiNode):
    """
    Write document pages for API node.
    :param writer: Writer object.
    :param api_node: ApiNode object.
    """

    log.info("API: {}".format(api_node.client_name))
    writer.add_class_header(api_node.client_name)

    # Parse class docstring.
    if api_node.doc is not None and len(api_node.doc) > 0:
        parser = DocstringParser(api_node.doc)

        if len(parser.descr) > 0:
            writer.add_paragraph(parser.descr)
            writer.ln(3)

        if parser.example is not None:
            writer.add_paragraph("Example:")
            writer.add_paragraph(parser.example, font_name=writer.monospace_font, indent=True)
            writer.ln(3)

    # Document class functions.
    for method in api_node.methods:
        write_api_method(writer, method, api_node.client_name)

    # Document class properties.
    if len(api_node.properties) != 0:
        writer.add_description("Properties:", None)

    for prop in api_node.properties:
        write_api_property(writer, prop, api_node.client_name)


def write_pdf_doc(api_nodes, output_path):
    """
    Write PDF document based on given API nodes.
    :param api_nodes: List of ApiNode objects.
    :param output_path: Output path where to write the document.
    """
    writer = PdfWriter()

    writer.add_title_page()

    writer.parse_markdown(os.path.join(writer.data_dir, 'intro.md'))

    module_names = []

    for api_node in api_nodes:
        if api_node.module_name not in module_names:
            module_names.append(api_node.module_name)

    module_names.sort()

    # Write API node documentation so that each module is a separate section.
    for module_name in module_names:
        writer.add_module_header(module_name)

        for api_node in api_nodes:
            if api_node.module_name != module_name:
                continue

            write_api_node(writer, api_node)

    writer.output(output_path)
