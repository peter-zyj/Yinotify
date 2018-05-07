Fork me on GitHub
Online reStructuredText editor
Editor
About
##
**
=
-
^
"
*
---------------
Bold
Italic
Monospace
---------------
Indent
Remove indent
---------------
Bulleted List
Numeric List
---------------
Picture
Link

========
Overview
========

*Yinotify* help user to create the callback function triggered when the monitor event detected by the linux Kernel. User could register the directoried for the watching and bing with the Event with the specified action. Internal Class Yivent could help to collect the statistics and status based on the events registered. That polling one or more directories to determine if anything has changed is the linux kernel interface, which help us control more from application level 

the project based on inotify, and removed some unused function and class



==========
Installing
==========

Install via *pip*::

    $ sudo pip install Yinotify


=======
Example
=======

Simple Usage::

    exp1:
        def printEvent():
            print("Action triggered!!")

        yiSample = Yinotify.fEvent(_target_folder,"IN_ISDIR",printEvent)

    exp2:
        def printEvent(arg):
            print("Action triggered!!",arg)

        yiSample = Yinotify.fEvent(_target_folder,"IN_ISDIR",printEvent,action_args=("arg1",))

=========
Unit Test
=========

Pytest Example::

    def printEvent(timeSlot,case):
        global result
        duration = time.time() - timeSlot
        print("%s:::Action1 triggered!!"%(duration))
        result[case] = True
        return

    def printEvent2(case):
        global result
        print("Action2 triggered!!")
        result[case] = True
        return

    def printEvent3():
        global result
        print("Action3 triggered!!")
        result["test_events_IN_MOVED"] = True
        return


    def test_events_IN_ISDIR():
        result["test_events_IN_ISDIR"] = False
        test1 = Yinotify.Yivent(folder,"IN_ISDIR",printEvent2,action_args=("test_events_IN_ISDIR",))
        cmd = "ls %s/" % (folder)
        print("test_events_IN_ISDIR::"+cmd)
        os.popen(cmd)
        n = 0
        while n < 2:
            time.sleep(1)
            n += 1
        del test1
        assert result["test_events_IN_ISDIR"] == True
        print("--------------------------------------------------------")

    def test_events_IN_OPEN():
        result["test_events_IN_OPEN"] = False
        timeSlot = time.time()
        test2 = Yinotify.Yivent(folder,"IN_OPEN",printEvent,action_args=(timeSlot,"test_events_IN_OPEN"))
        cmd = "touch %s/Yijun2" % (folder)
        print("test_events_IN_OPEN::"+cmd)
        os.popen(cmd)
        n = 0
        while n < 2:
            time.sleep(1)
            n += 1
        del test2

        assert result["test_events_IN_OPEN"] == True
        print("--------------------------------------------------------")


    def test_events_IN_MOVED():
        result["test_events_IN_MOVED"] = False
        test3 = Yinotify.Yivent(folder,"IN_MOVED_FROM,IN_MOVED_TO",printEvent3)
        cmd = "mv %s/Yijun2 %s/Yijun22" % (folder,folder)
        print("test_events_IN_MOVED::"+cmd)
        os.popen(cmd)
        n = 0
        while n < 2:
            time.sleep(1)
            n += 1
        del test3
        assert result["test_events_IN_MOVED"] == True
        print("--------------------------------------------------------")



    def test_events_IN_CREATE():
        result["test_events_IN_CREATE"] = False
        timeSlot = time.time()
        test4 = Yinotify.Yivent(folder,"IN_CREATE",printEvent,action_args=(timeSlot,"test_events_IN_CREATE"))
        os.mkdir(folder+'/Yijun3')
        print("test_events_IN_CREATE::os.mkdir(folder+'/Yijun3')")

        n = 0
        while n < 2:
            time.sleep(1)
            n += 1
        del test4

        assert result["test_events_IN_CREATE"] == True
        print("--------------------------------------------------------")

    def test_events_IN_DELETE():
        result["test_events_IN_DELETE"] = False
        timeSlot = time.time()
        test5 = Yinotify.Yivent(folder,"IN_DELETE",printEvent,action_args=(timeSlot,"test_events_IN_DELETE"))
        os.remove(folder+"/Yijun22")
        os.rmdir(folder+"/Yijun3")
        print("test_events_IN_DELETE::os.remove(folder+'/Yijun2')")

        n = 0
        while n < 2:
            time.sleep(1)
            n += 1
        del test5

        assert result["test_events_IN_DELETE"] == True
        print("--------------------------------------------------------")
