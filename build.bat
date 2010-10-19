c:\python27\python.exe setup.py clean
c:\python27\python.exe setup.py install
c:\python27\python.exe setup.py bdist_wininst
c:\python27\python.exe setup.py sdist --formats=gztar,zip
copy dist\*.* c:\pub\arcrest
copy documentation\html\*.* c:\pub\arcrest\documentation\
c:\python27\python.exe mergeifneeded.py
hg history > c:\pub\arcrest\changelog.txt
unix2dos c:\pub\arcrest\changelog.txt
del c:\pub\arcrest\*.bak
hg push c:\pub\arcrest\src\
cd c:\pub\arcrest\src\
hg update
