import select
import os,sys,re,datetime
import time,logging
import struct
import collections
from multiprocessing import Process,Manager

from errno import EINTR

import Yinotify.constants
import Yinotify.calls

# Constants.

_DEFAULT_EPOLL_BLOCK_DURATION_S = 1
_HEADER_STRUCT_FORMAT = 'iIII'

_DEFAULT_TERMINAL_EVENTS = (
    'IN_Q_OVERFLOW',
    'IN_UNMOUNT',
)

# Globals.

_LOGGER = logging.getLogger(__name__)

_INOTIFY_EVENT = collections.namedtuple(
                    '_INOTIFY_EVENT',
                    [
                        'wd',
                        'mask',
                        'cookie',
                        'len',
                    ])

_STRUCT_HEADER_LENGTH = struct.calcsize(_HEADER_STRUCT_FORMAT)
_IS_DEBUG = bool(int(os.environ.get('DEBUG', '0')))



class TerminalEventException(Exception):
    def __init__(self, type_name, event):
        super(TerminalEventException, self).__init__(type_name)
        self.event = event


class YiError(Exception):
    def __init__(self, description):
        super(YiError, self).__init__(description)



class Inotify(object):
    def __init__(self, paths=[], block_duration_s=_DEFAULT_EPOLL_BLOCK_DURATION_S):
        self.__block_duration = block_duration_s
        self.__watches = {}
        self.__watches_r = {}
        self.__buffer = b''

        self.__inotify_fd = Yinotify.calls.inotify_init()
        _LOGGER.debug("Yinotify handle is (%d).", self.__inotify_fd)

        self.__epoll = select.epoll()
        self.__epoll.register(self.__inotify_fd, select.POLLIN)

        self.__last_success_return = None

        for path in paths:
            self.add_watch(path)

    def __get_block_duration(self):
        """Allow the block-duration to be an integer or a function-call."""

        try:
            return self.__block_duration()
        except TypeError:
            # A scalar value describing seconds.
            return self.__block_duration

    def __del__(self):
        _LOGGER.debug("Cleaning-up Yinotify.")
        os.close(self.__inotify_fd)

    def add_watch(self, path_unicode, mask=Yinotify.constants.IN_ALL_EVENTS):
        _LOGGER.debug("Adding watch: [%s]", path_unicode)

        # Because there might be race-conditions in the recursive handling (see
        # the notes in the documentation), we recommend to add watches using
        # data from a secondary channel, if possible, which means that we might
        # then be adding it, yet again, if we then receive it in the normal
        # fashion afterward.
        if path_unicode in self.__watches:
            _LOGGER.warning("Path already being watched: [%s]", path_unicode)
            return

        path_bytes = path_unicode.encode('utf8')

        wd = Yinotify.calls.inotify_add_watch(self.__inotify_fd, path_bytes, mask)
        _LOGGER.debug("Added watch (%d): [%s]", wd, path_unicode)

        self.__watches[path_unicode] = wd
        self.__watches_r[wd] = path_unicode

        return wd

    def remove_watch(self, path, superficial=False):
        """Remove our tracking information and call inotify to stop watching
        the given path. When a directory is removed, we'll just have to remove
        our tracking since Yinotify already cleans-up the watch.
        """

        wd = self.__watches.get(path)
        if wd is None:
            return

        _LOGGER.debug("Removing watch for watch-handle (%d): [%s]",
                      wd, path)

        del self.__watches[path]

        self.remove_watch_with_id(wd)

    def remove_watch_with_id(self, wd, superficial=False):
        del self.__watches_r[wd]

        if superficial is False:
            _LOGGER.debug("Removing watch for watch-handle (%d).", wd)

            Yinotify.calls.inotify_rm_watch(self.__inotify_fd, wd)

    def _get_event_names(self, event_type):
        names = []
        for bit, name in Yinotify.constants.MASK_LOOKUP.items():
            if event_type & bit:
                names.append(name)
                event_type -= bit

                if event_type == 0:
                    break

        assert event_type == 0, \
               "We could not resolve all event-types: (%d)" % (event_type,)

        return names

    def _handle_inotify_event(self, wd, event_type):
        """Handle a series of events coming-in from inotify."""

        names = self._get_event_names(event_type)

        b = os.read(wd, 1024)
        if not b:
            return

        self.__buffer += b

        while 1:
            length = len(self.__buffer)

            if length < _STRUCT_HEADER_LENGTH:
                _LOGGER.debug("Not enough bytes for a header.")
                return

            # We have, at least, a whole-header in the buffer.

            peek_slice = self.__buffer[:_STRUCT_HEADER_LENGTH]

            header_raw = struct.unpack(
                            _HEADER_STRUCT_FORMAT,
                            peek_slice)

            header = _INOTIFY_EVENT(*header_raw)
            type_names = self._get_event_names(header.mask)

            event_length = (_STRUCT_HEADER_LENGTH + header.len)
            if length < event_length:
                return

            filename = self.__buffer[_STRUCT_HEADER_LENGTH:event_length]

            # Our filename is 16-byte aligned and right-padded with NULs.
            filename_bytes = filename.rstrip(b'\0')

            self.__buffer = self.__buffer[event_length:]

            path = self.__watches_r.get(header.wd)
            if path is not None:
                filename_unicode = filename_bytes.decode('utf8')
                yield (header, type_names, path, filename_unicode)

            buffer_length = len(self.__buffer)
            if buffer_length < _STRUCT_HEADER_LENGTH:
                break

    def event_gen(
        self, timeout_s=None, yield_nones=True, filter_predicate=None,
        terminal_events=_DEFAULT_TERMINAL_EVENTS):

        # We will either return due to the optional filter or because of a
        # timeout. The former will always set this. The latter will never set
        # this.
        self.__last_success_return = None

        last_hit_s = time.time()


        def filter(type_name,event):
            if type_name in event[1]:
                return False
            else:
                return True
            

        while True:
            block_duration_s = self.__get_block_duration()

            # Poll, but manage signal-related errors.

            try:
                events = self.__epoll.poll(block_duration_s)
            except IOError as e:
                if e.errno != EINTR:
                    raise

                if timeout_s is not None:
                    time_since_event_s = time.time() - last_hit_s
                    if time_since_event_s > timeout_s:
                        break

                continue

            # Process events.

            for fd, event_type in events:
                # (fd) looks to always match the inotify FD.

                for (header, type_names, path, filename) \
                        in self._handle_inotify_event(fd, event_type):
                    last_hit_s = time.time()

                    e = (header, type_names, path, filename)
                    for type_name in type_names:
                        if filter_predicate is not None and \
                           eval(filter_predicate)(type_name, e) is False:
                             print(e)
                             self.__last_success_return = (type_name, e)
                             return
                        elif type_name in terminal_events:
                            raise TerminalEventException(type_name, e)

                    yield e

            if timeout_s is not None:
                time_since_event_s = time.time() - last_hit_s
                if time_since_event_s > timeout_s:
                    break

            if yield_nones is True:
                yield None

    @property
    def last_success_return(self):
        return self.__last_success_return


class Yivent(object):
    def __init__(self,fileName,event=None,action=None,action_args=None,times=None):
        timeSlot = str(datetime.datetime.now())
        _LOGGER.debug(timeSlot+"::"+"Yivent Initialization")

        self.name = fileName.strip()
        self.wd = None

        manager_obj1 = Manager()
        self.actions = manager_obj1.dict()

        manager_obj2 = Manager()
        self.events = manager_obj2.dict()

        manager_obj3 = Manager()
        self.times = manager_obj3.dict()     #detected events number

        self.p1 = None
        self.p2 = None
        self.action_args = {}
        self.deps = {}

        if event:
            event = event.strip().upper()

            if not self.wd:
                self.wd = Inotify()

            for et in event.split(","):
                self.wd.add_watch(self.name)
                self.events[et] = 0

        self.dependsAdd(event)

        if action and event:
            self.actions[event] = action
            self.action_args[action] = action_args


        if event and action and times:
            if times > 9999:
                self.times[event] = 9999   #forever
            else:
                self.times[event] = times
        else:
            self.times[event] = 1

        tEvents = dict(self.events)

        self.p1 = Process(target=self.loopCheck, args=(tEvents,))
        self.p1.start()

        if action and event:
            self.p2 = Process(target=self.execute_action, args=(event,))
            self.p2.start()


    def dependsAdd(self,eventList):
        elist = eventList.split(",")
        for event in elist:
            try:
                if self.deps[event]:
                    print("ERR:Dependency Check failed by Event Depends Existed! ")
                    timeSlot = str(datetime.datetime.now())
                    _LOGGER.debug(timeSlot+"::"+"ERR:Dependency Check failed by Event Depends Existed!")
                    self.__del__()
                    raise YiError(YiException,"ERR:Dependency Check failed by Event Depends Existed!")

            except KeyError:
                if elist.index(event) != 0:
                    self.deps[event] = elist[elist.index(event)-1]
                else:
                    self.deps[event] = None

#   def dependsCheck(self,eventList):
#       "TBD"
    def triggerCheck(self,eventList):
        elist = eventList.split(",")
#       print("debug1::",elist)
#       print("debug2::",self.events)
        if self.deps != {}:
            res1 = [self.deps[x] for x in elist]
            res2 = [self.events[y] for y in elist]
            if 0 not in res2:
                return True
            else:
#               print("debug3::",res2)
                return False
        else:
            timeSlot = str(datetime.datetime.now())
            _LOGGER.debug(timeSlot+"::"+"ERR:Trigger Check Check failed by empty dependancy dictionary!")
            self.__del__()
            raise YiError(YiException,"ERR:Trigger Check Check failed by empty dependancy dictionary!")

    def execute_action(self,event):
        print ("actions1")
        cnt = self.times[event]

        while True:
#           if cnt >=1 and self.events[event]>0 and not self.dependsCheck(event):
            if cnt >=1 and self.triggerCheck(event): 
                print ("actions2")
                try:
                    print("Debug:execute_action:",event)
                    action = self.actions[event]
                    if not self.action_args[action]:
                        Process(target=self.actions[event], args=()).start()
                    else:
                        Process(target=self.actions[event], args=self.action_args[action]).start()
                    if self.times[event]>0 and self.times[event]<9999:
                        cnt -= 1
                    time.sleep(1)
                except KeyError:
                    print ("there is no such Event:[%s] registered"%(event))
            else:
                if cnt == 0:
                    break
                else:
                    continue

    def loopCheck(self,tEvents):   
        if self.wd:
            for event in self.wd.event_gen(yield_nones=False):
                print ("Detected:loopCheck:",event)
                for x in tEvents.keys():
                    if x in event[1]:
                        self.events[x] += 1
                        print(self.events)


    def registerEvent(self,event):
        event = event.strip().upper()
        if not self.wd:
            self.wd = Yinotify.adapters.Inotify()
        self.wd.add_watch(self.name)
        self.events[event] = 0



    def registerAction(self,event,action):
        event = event.strip()
        action = action.strip()
        self.actions[event] = action


    def showEvent(self):
        return self.events

    def eventCheck(self,event):
        if event in self.events and self.events[event] > 0:
            return True
        elif event not in self.events:
            return None
        else:
            return False


    def __del__(self):
        self.wd.remove_watch(self.name)
        if self.p1:
            self.p1.terminate()
            self.p1 = None

        if self.p2:
            self.p2.terminate()
            self.p2 = None

        self.name = None
        self.events = None
        self.actions = None
        del self.wd
        timeSlot = str(datetime.datetime.now())
        _LOGGER.debug(timeSlot+"::"+"Yivent CleanUp")

