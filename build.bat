c:\python26\python.exe setup.py clean
c:\python26\python.exe setup.py install
c:\python26\python.exe setup.py bdist_wininst
c:\python26\python.exe setup.py sdist --formats=gztar,zip
copy dist\*.* \\ironpaw\pub\jasons\arcrest
copy documentation\html\*.* \\ironpaw\pub\jasons\arcrest\documentation\
python mergeifneeded.py
hg history > \\ironpaw\pub\jasons\arcrest\changelog.txt
unix2dos \\ironpaw\pub\jasons\arcrest\changelog.txt
del \\ironpaw\pub\jasons\arcrest\*.bak
