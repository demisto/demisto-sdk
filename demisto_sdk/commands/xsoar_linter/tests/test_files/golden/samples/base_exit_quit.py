"""Sample: exit() and quit() calls (E9004, E9005)."""

import os
import sys

exit()
exit(0)
exit(1)
quit()
quit(1)
sys.exit(1)
os._exit(1)
builtins.exit()
builtins.quit()
