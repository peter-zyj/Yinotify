#!/usr/local/bin/python3
import os,sys,re,datetime
import time,logging
from inotify import adapters
from inotify.adapters import Inotify
from inotify.adapters import TerminalEventException
from multiprocessing import Process,Manager


_LOGGER = logging.getLogger(__name__)

class Inotify2(Inotify):
#   def __init__(self, paths=[], block_duration_s=adapters._DEFAULT_EPOLL_BLOCK_DURATION_S):
#       super().__init__(paths=[], block_duration_s=adapters._DEFAULT_EPOLL_BLOCK_DURATION_S)


#    def __del__(self):
#       self._LOGGER.debug("Cleaning-up inotify.")
#       logging.debug("Cleaning-up Yinotify.")
#       os.close(self._Inotify__inotify_fd)

     def event_gen(
            self, timeout_s=None, yield_nones=True, filter_predicate=None,
            terminal_events=adapters._DEFAULT_TERMINAL_EVENTS):
        """Yield one event after another. If `timeout_s` is provided, we'll
        break when no event is received for that many seconds.
        """

        # We will either return due to the optional filter or because of a
        # timeout. The former will always set this. The latter will never set
        # this.
        self._Inotify__last_success_return = None

        last_hit_s = time.time()


        def filter(type_name,event):
            if type_name in event[1]:
                return False
            else:
                return True
            

        while True:
            block_duration_s = self._Inotify__get_block_duration()

            # Poll, but manage signal-related errors.

            try:
                events = self._Inotify__epoll.poll(block_duration_s)
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
                             self._Inotify__last_success_return = (type_name, e)
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


class fEvent(object):
    def __init__(self,fileName,event=None,action=None,times=None):
        timeSlot = str(datetime.datetime.now())
        _LOGGER.debug(timeSlot+"::"+"Yinotify Initialization")

        self.name = fileName.strip()
        self.wd = None

        manager_obj1 = Manager()
        self.actions = manager_obj1.dict()

        manager_obj2 = Manager()
        self.events = manager_obj2.dict()

        manager_obj3 = Manager()
        self.times = manager_obj3.dict()     #detected events number

        if event:
            event = event.strip().upper()
            if not self.wd:
                self.wd = Inotify2()

            self.wd.add_watch(self.name)
            self.events[event] = 0

        if action and event:
            self.actions[event] = action


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


    def loopExecution(self):
        "TBD"


    def execute_action(self,event):
        print ("actions1")
        cnt = self.times[event]
        while True:
            if cnt >=1 and self.events[event]>0:
                print ("actions2")
                try:
                    print("Debug:execute_action:",event)
                    Process(target=self.actions[event], args=()).start()
                    if self.times[event]>0 and self.times[event]<9999:
                        cnt -= 1
#                   if self.times[event] > 9999 and self.events[event]>0:
#                       Process(target=self.actions[event], args=()).start()
#                   elif self.times[event]>0:
#                       Process(target=self.actions[event], args=()).start()
#                       cnt -= 1
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
                        print(self.events)
                        print(self.events[x])
                        self.events[x] += 1
                        "TBD-actions"
#                       if self.times[x]>0:
#                           self.actions[x]()
#                           self.times[x] -= 1


    def registerEvent(self,event):
        event = event.strip().upper()
        if not self.wd:
            self.wd = inotify.adapters.Inotify()
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
        self.p1.terminate()
        self.p2.terminate()
        self.name = None
        self.events = None
        self.actions = None
        timeSlot = str(datetime.datetime.now())
        _LOGGER.debug(timeSlot+"::"+"Yinotify CleanUp")

