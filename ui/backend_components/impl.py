from __future__ import annotations

from .common import *
from .conversion_controls import BODY as CONVERSION_BODY
from .core import BODY as CORE_BODY
from .downloads import BODY as DOWNLOADS_BODY
from .event_loop import BODY as EVENT_LOOP_BODY
from .ffmpeg_paths import BODY as FFMPEG_PATHS_BODY
from .general_properties import BODY as GENERAL_PROPERTIES_BODY
from .media_details import BODY as MEDIA_DETAILS_BODY
from .queue_actions import BODY as QUEUE_ACTIONS_BODY
from .queue_io import BODY as QUEUE_IO_BODY
from .ui_preferences import BODY as UI_PREFERENCES_BODY


_CLASS_SOURCE = (
    'class Backend(QtCore.QObject):\n'
    '    """Qt/QML backend assembled from focused source components."""\n'
    '    __module__ = "ui.backend"\n'
    + CORE_BODY
    + GENERAL_PROPERTIES_BODY
    + UI_PREFERENCES_BODY
    + QUEUE_IO_BODY
    + FFMPEG_PATHS_BODY
    + DOWNLOADS_BODY
    + QUEUE_ACTIONS_BODY
    + MEDIA_DETAILS_BODY
    + CONVERSION_BODY
    + EVENT_LOOP_BODY
)

_namespace = dict(globals())
exec(compile(_CLASS_SOURCE, "ui/backend_components/assembled_backend.py", "exec"), _namespace)
Backend = _namespace["Backend"]
