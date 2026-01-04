# Use dev settings as default, use production if dev settings do not exist
# ruff: noqa
try:
    from .dev import *
except:
    from .prod import *
