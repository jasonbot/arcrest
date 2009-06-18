c:\python26\python.exe setup.py clean
c:\python26\python.exe setup.py install
c:\python26\python.exe setup.py bdist_wininst
c:\python26\python.exe setup.py sdist --formats=gztar,zip
copy dist\*.* c:\pub\arcrest
copy documentation\html\*.* c:\pub\arcrest\documentation\
python mergeifneeded.py
hg history > c:\pub\arcrest\changelog.txt
unix2dos c:\pub\arcrest\changelog.txt
del c:\pub\arcrest\*.bak
