import sys, os
print('script cwd:', os.getcwd())
print('sys.path[0]:', sys.path[0])
try:
    import main
    print('import main ok')
except Exception as e:
    import traceback
    traceback.print_exc()
    raise
