rgcompare
=========

rgkit robot comparison tool
----

This is a program to compare two (soon: many) rgkit robots (see also robotgame.org). 

Features
----
It has multiprocessing and live updating of graphs.

It is in some sorts a replacement for rgkit's default 'run-headless.py', since it is supposed to only test bots against each other, and not be
used for debugging. Try to use non-functional bots at your own peril!

Requirements
----

Python 2.7 (plus its standard libraries), matplotlib, numpy,
[rgkit] [1]

[1]: https://github.com/brandonhsiao/rgkit "rgkit"


Caveats
----

I'm not a (professional) programmer, so please excuse my coding style, should it be non-standard or bad. 
If there's something you want to change, feel free to contribute. There are also numerous bugs currently,
the program is unresponsive when running and it will occasinally crash. Don't say I didn't warn you.

Example
----

![](http://i.imgur.com/kiBKUjT.png)

![](http://i.imgur.com/bMXlC7G.png)


Usage
----

    
    usage: rgcompare [-h] [--initrun] [--games GAMES] [--turns TURNS] [--version]
                     [--processes PROCESSES] [--batch [output dir]] [--no-gui]
                     [--map MAP]
                     [r [r ...]]
    
    Compare two or more robotgame controller bots in rgkit
    
    positional arguments:
      r                     robots to fight each other. not yet implemented: if
                            more than two, batch mode will commence
    
    optional arguments:
      -h, --help            show this help message and exit
      --initrun             attempt to run game as soon as launched
      --games GAMES         number of games to run (default 100)
      --turns TURNS         number of turns per run to set (default 100)
      --version             show program's version number and exit
      --processes PROCESSES
                            number of processors to use for calculation (default
                            NUM_PROCESSORS)
      --batch [output dir]  not yet implemented: and save image of every battle
                            when finished (default: rgcompare/)
      --no-gui              run without graphics (enables initial run)
      --map MAP             map to use (default maps/default.py)
