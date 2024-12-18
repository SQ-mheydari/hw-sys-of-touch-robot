# User manual

User manual is a single self-contained document designed for Touch customers. It goes into details for
how to use Touch system and related software including TnT Server and TnT UI.

User manual is developed in Latex source format and parts of it are generated from Markdown files which
are maintained in TnT UI repository.

This document instructs how to compile the document.

TODO: Add easy quick instructions for updating the document and instruction that which files should be included to version control

## Setting up for Windows

- Install Miktex by downloading installer from https://miktex.org/download .
- Update Miktex by using Miktex Console from Windows Start menu.
- Latex should now be available in command-line.

## Compiling to PDF

Run `compile.bat` under `doc/user_manual/`:

The PDF file should be created in the run directory.

## Known issues

- The three etoolbox warnings that come up during compilation are ok. The effect they cause is that if there are syntax errors in code blocks the errors are highlighted with red boxes which doesn't look that nice 