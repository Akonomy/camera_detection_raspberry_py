import os
import sys



project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..'))
if project_root not in sys.path:
    sys.path.append(project_root)


from SOURCES.WEB.handler_container import request_box

from DATABASE import db


# <<< CONFIGURABIL >>>
BOX_CODE = "SGsYp36"
CONTAINER_CODE = "SGsYp36"  # Poate fi același sau altul

info=request_box(CONTAINER_CODE)

print(info)