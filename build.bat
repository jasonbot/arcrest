c:\python25\python.exe setup.py bdist_wininst
c:\python25\python.exe setup.py sdist --formats=gztar,zip
copy dist\*.* \\ironpaw\pub\jasons\arcrest
copy documentation\html\*.* \\ironpaw\pub\jasons\arcrest\documentation\
"C:\Program Files\WinMerge\WinMergeU.exe" tests.py \\ironpaw\pub\jasons\arcrest\tests.py
hg history > \\ironpaw\pub\jasons\arcrest\changelog.txt
