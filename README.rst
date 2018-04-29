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

        yiSample = Yinotify.fEvent(_target_folder,"IN_ISDIR",printEvent,arg)


