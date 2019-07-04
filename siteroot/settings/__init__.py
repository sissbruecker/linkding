# Use dev settings as default, use production if dev settings do not exist
try:
    from .dev import *
except:
    from .prod import *
