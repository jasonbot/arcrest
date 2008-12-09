import os
import sha

def mergeifneeded(file1, file2):
    cs1, cs2 = sha.new(open(file1).read()).hexdigest(), \
               sha.new(open(file2).read()).hexdigest()
    if cs1 != cs2:
        os.popen(r'"C:\Program Files\WinMerge\WinMergeU.exe" %s %s' % 
                   (file1, file2))

mergeifneeded(r"tests.py", r"\\ironpaw\pub\jasons\arcrest\tests.py")
mergeifneeded(r"gui.py", r"\\ironpaw\pub\jasons\arcrest\gui.py")
mergeifneeded(r"guitest.py", r"\\ironpaw\pub\jasons\arcrest\guitest.py")
mergeifneeded(r"messageinabottle.py", r"\\ironpaw\pub\jasons\arcrest\messageinabottle.py")
