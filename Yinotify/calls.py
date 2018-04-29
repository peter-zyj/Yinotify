import logging
import ctypes

import Yinotify.library

_LOGGER = logging.getLogger(__name__)

_LIB = Yinotify.library.instance


inotify_init = _LIB.inotify_init


inotify_add_watch = _LIB.inotify_add_watch

inotify_rm_watch = _LIB.inotify_rm_watch


