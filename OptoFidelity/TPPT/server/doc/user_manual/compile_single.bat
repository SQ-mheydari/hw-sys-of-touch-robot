REM Run latex commands a few times to resolve all references
REM Give tex file as command line argument

REM Full manual

rmdir output /S /Q
rmdir directory=auxiliary /S /Q

xelatex.exe -synctex=1 -interaction=nonstopmode %1 -shell-escape -output-directory=output -aux-directory=auxiliary
xelatex.exe -synctex=1 -interaction=nonstopmode %1 -shell-escape -output-directory=output -aux-directory=auxiliary
xelatex.exe -synctex=1 -interaction=nonstopmode %1 -shell-escape -output-directory=output -aux-directory=auxiliary

