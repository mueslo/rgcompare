rgcompare
=========

rgkit robot comparison tool
----

this is a program to compare two rgkit robots (see also robotgame.org)

Requirements
----

Python 2.7 (plus its standard libraries), matplotlib, numpy,
[rgkit] [1]

[1]: https://github.com/brandonhsiao/rgkit "rgkit"


Caveats
----

I'm not a (professional) programmer, so please excuse my coding style. If there's something you want to change,
feel free to contribute. There are also numerous bugs currently, the program is unresponsive when running and
it will occasinally crash. Don't say I didn't warn you.

Example
----

![](http://i.imgur.com/kiBKUjT.png)

![](http://i.imgur.com/bMXlC7G.png)


Usage
----

output is currently always graphical, but nearly everything (except for saving image)
can be done on the command line:
    
    usage: rgcompare [-h] [--initrun] [--runs RUNS] [--turns TURNS] [--version]
                     [--processes PROCESSES] [--batch [output dir]] [--map MAP]
                     [r [r ...]]
    
    Compare two or more robotgame controller bots in rgkit
    
    positional arguments:
      r                     robots to fight each other. not yet implemented: if
                            more than two, batch mode will commence
    
    optional arguments:
      -h, --help            show this help message and exit
      --initrun             attempt to run game as soon as launched
      --runs RUNS           number of runs to set (default 100)
      --turns TURNS         number of turns per run to set (default 100)
      --version             show program's version number and exit
      --processes PROCESSES
                            number of processors to use for calculation (default
                            NUM_PROCESSORS)
      --batch [output dir]  not yet implemented: don't create gui, and save image
                            of every battle when finished (default: rgcompare/)
      --map MAP             map to use (default maps/default.py)
