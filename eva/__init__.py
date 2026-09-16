from eva.brain import *

import sys
import eva
if 'irene' not in sys.modules:
    sys.modules['irene'] = eva
    sys.modules['irene.brain'] = eva.brain
