:: Change this to the TnT Server doc location on your system.
set SERVER_DOC_PATH=..\..\..\..\tnt_server_gt\doc
cd text

:: Run pandoc for all markdown files to convert them into latex files to be added to the document later
for %%f in (*.md) do (
    pandoc %%f -f markdown -t latex -o "%%~nf.tex")
)

cd ..
python prepare_images_for_user_manual.py

:: Copy the generated .tex files to server directory for inclusion in the user manual there
:: Assumes .bat running directory of "tnt_ui_gt\tnttool\res\help_content\text" and that "tnt_server_gt" and "tnt_ui_gt" folders are in the same parent folder
:: /y: suppress prompts
xcopy /y "text\*.tex" %SERVER_DOC_PATH%\user_manual\from_ui_repo\*.tex

:: /y: suppress prompts
:: /i: destination is a directory that is created if doesnt exist.
xcopy /y /i images "%SERVER_DOC_PATH%\images\ui_help_images"