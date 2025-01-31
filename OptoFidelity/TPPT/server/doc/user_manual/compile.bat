REM Run latex commands a few times to resolve all references

REM Full manual

rmdir output /S /Q
rmdir directory=auxiliary /S /Q

copy user_manual.tex tnt_user_manual.tex
call compile_single.bat tnt_user_manual.tex
copy output\tnt_user_manual.pdf .

REM HSUF manual

rmdir output /S /Q
rmdir directory=auxiliary /S /Q

type user_manual.tex | findstr /v "\include{hsup}" | findstr /v "\include{dut_applications}" | findstr /v "\include{tppt}" > tnt_user_manual_hsuf.tex
call compile_single.bat tnt_user_manual_hsuf.tex
copy output\tnt_user_manual_hsuf.pdf .

REM HSUP manual

rmdir output /S /Q
rmdir directory=auxiliary /S /Q

type user_manual.tex | findstr /v "\include{hsuf}" | findstr /v "\include{tppt}" > tnt_user_manual_hsup.tex
call compile_single.bat tnt_user_manual_hsup.tex
copy output\tnt_user_manual_hsup.pdf .

REM TPPT manual

rmdir output /S /Q
rmdir directory=auxiliary /S /Q

type user_manual.tex | findstr /v "\include{hsuf}" | findstr /v "\include{hsup}" > tnt_user_manual_tppt.tex
call compile_single.bat tnt_user_manual_tppt.tex
copy output\tnt_user_manual_tppt.pdf .

if exist "tnt_user_manual.pdf" (exit /b 0)
