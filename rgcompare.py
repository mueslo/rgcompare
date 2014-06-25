#!/usr/bin/env python2

#import system stuff
import sys
import time
import os
import multiprocessing
import Queue

#imgur stuff
import tempfile
from base64 import b64encode
import json
import urllib
import urllib2
import webbrowser

#import GUI stuff
import Tkinter as Tk
import tkMessageBox
import tkFileDialog

#import plotting stuff
import matplotlib as mpl

mpl.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import colors
import numpy as np

#import RG stuff
from rgkit import game, rg
import ast
from rgkit.settings import settings

#whether to produce game logs
log = True

#current version, increasing this won't make it any better, sadly
version = "0.2"

#for imgur api
client_id = 'dc694fab186fc6e'

#windows compatibility stuff
pm = None
if sys.stdout.encoding in ["UTF-8", "UTF8", "UTF-16", "UTF16"]:
    pm = u"\u00b1"
else:
    pm = "+-"


#functionality that seems to be  missing in os.path:
# splits "/path/to/file.withext" into ("/path/to/","file",".withext")
def split(path):
    path = str(path)
    split_path = list(os.path.split(path))
    if split_path[0] not in ["", "/"]:
        split_path[0] += "/"
    split_ext = os.path.splitext(split_path[1])
    return split_path[0], split_ext[0], split_ext[1]


K_FACTOR = 32


def new_rating(r1, r2, result):
    expected = 1 / (1 + pow(10, (r2 - r1) / 400))
    return r1 + K_FACTOR * (result - expected)


class PlayerList():
    def __init__(self, parent, fnames, minsize=2):
        print "Creating Player List"
        self.players = []

        if type(fnames) == str:
            fnames = [fnames]

        self.parent = parent

        for f in fnames:
            self.players.append(self.create_player(f))

        #if batch mode, filter players
        if len(self.players) > 2:
            self.players = filter(None, self.players)

        #no elif since the part immediately above may reduce size
        if len(self.players) < 2:
            #pad with None
            self.players += (minsize - len(self.players)) * [None]

    def names(self, validonly=True):
        return [p.name for p in self.players if p is not None or not validonly]

    def fnames(self, validonly=True):
        return [p.fname for p in self.players if p is not None or not validonly]

    def runnable(self):
        if None in self.players:
            return False
        else:
            return True

    @staticmethod
    def create_player(fname):
        if fname is None or not os.path.isfile(fname):
            return None
        else:
            return Player(fname)

    def __setitem__(self, i, fname):
        self.players[i] = self.create_player(fname)

    def __iter__(self):
        return iter(self.players)

    def __getitem__(self, i):
        return self.players[i]

    def __str__(self):
        return ", ".join(str(p) for p in self.players)


class Player():
    def __init__(self, fname):
        self.fname = fname
        self.name = split(fname)[1]
        self.score = 0

    def __str__(self):
        return self.name


class RedirectStdStreams(object):
    def __init__(self, stdout=None, stderr=None):
        self.old_stdout, self.old_stderr = None, None
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self):
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


class RCReplaceDialog(Tk.Toplevel):
    def __init__(self, parent, fname):
        Tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.fname = fname
        self.transient(parent)

        Tk.Label(self, text="Which robot would you like to replace with {0}?".format(os.path.basename(fname))).pack()
        Tk.Button(self, text=str(parent.players[0]), command=self.replace0).pack(side=Tk.LEFT)
        Tk.Button(self, text=str(parent.players[1]), command=self.replace1).pack(side=Tk.RIGHT)

        self.wait_window()

    def replace0(self):
        self.parent.players[0] = self.fname
        self.destroy()

    def replace1(self):
        self.parent.players[1] = self.fname
        self.destroy()


#This is the workhorse. It continually checks the work queue for new work
# and then returns the resulting score and time it took
def comparison_worker(identity, input, output):
    logfile = open(os.getcwd() + "/" + "rgcompare" + "." + str(identity) + ".log", 'w') if log else open(os.devnull, 'w')
    print "Starting worker {0} (logging to {1})".format(identity, logfile.name)
    try:
        with RedirectStdStreams(stdout=logfile, stderr=logfile):
            for match_id, player_fnames, map_fname, turns in iter(input.get, 'STOP'):

                map_data = ast.literal_eval(open(map_fname).read())
                settings.init_map(map_data)
                players = [game.Player(x) for x in player_fnames]
                g = game.Game(players)

                t_start = time.clock()
                for i in range(turns):
                    print (' running turn %d ' % g._state.turn).center(70, '-')
                    g.run_turn()
                t_end = time.clock()

                output.put([g.get_scores(), t_end - t_start])
    finally:
        print "Terminating worker {0}...".format(identity)


#This is the graphical comparison tool itself
class RobotComparison(Tk.Tk):
    def __init__(self, parent, map_fname, player_fnames=[None, None], processes=0, samples=100, turns=0, initrun=False,
                 batch=False, show=True):
        self.show = show

        if self.show:
            Tk.Tk.__init__(self)

        #get arguments
        self.parent = parent

        if processes > multiprocessing.cpu_count():
            print "Warning: more processes than cores, you will gain little performance advantage, and the game " \
                  "timings will be wrong."
        #bear in mind: self.processes is a list of multiprocessing.Process()es
        #           while the argument is just an int
        self.processes = [None] * processes if processes > 0 else [None] * multiprocessing.cpu_count()

        self.turns = turns or settings.max_turns

        self.map_fname = map_fname

        self.run_samples = samples  # num games to compare

        #do intialization stuff
        if self.show:
            self.setup_UI()
        self.players = PlayerList(self, player_fnames)

        self.initialize()

        if self.show and not self.players.runnable():
            self.menubar.entryconfigure('Run', state=Tk.DISABLED)

        try:
            if initrun:
                if self.players.runnable():
                    self.run()
                else:
                    print "Can't run this configuration of players."
                    if self.show:
                        tkMessageBox.showwarning("Run", "Can't run this configuration of players.")

            if self.show:
                self.mainloop()
        except KeyboardInterrupt:
            self.abort()
        finally:
            for _ in self.processes:
                self.task_queue.put('STOP')

    def initialize(self):
        print "Initialising with players", str(self.players)
        self.task_queue = multiprocessing.Queue()
        self.done_queue = multiprocessing.Queue()
        self.tasks_finished = 0
        self.target_samples = 0
        self.running = False
        self.results = []
        self.runtimes = []
        self.winners = []

        #UI stuff:
        if self.show:
            if not self.players.runnable():
                self.menubar.entryconfigure('Run', state=Tk.DISABLED)
            else:
                self.menubar.entryconfigure('Run', state=Tk.NORMAL)

            #label stuff due to fnames
            for i, p in enumerate(self.players):
                self.lines[i].set_label(str(p))  # cast is necessary for some backwards compat

            self.ax.legend(ncol=2)
            self.ax2.set_ylabel(self.players[0])
            self.ax2.set_xlabel(self.players[1])
            self.ax.set_title("{0} {1}:{2} {3}".format(self.players[0], self.winners.count(0), self.winners.count(1),
                                                       self.players[1]))
            self.canvas.draw()

    def placebo(self):
        pass

    def setup_UI(self):
        #plt.rc('text', usetex=True)
        #plt.rc('font', family='sans-serif')

        import matplotlib.gridspec as gridspec

        self.menubar = Tk.Menu(self)

        self.filemenu = Tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open robot", command=self.open_robot)
        self.filemenu.add_command(label="Save plot", command=self.save_plot)
        self.filemenu.add_command(label="Upload to Imgur", command=self.upload_imgur)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.menubar.add_command(label="Run", command=self.run, state='disabled')
        self.menubar.add_command(label="Quit", command=self.close)
        self.config(menu=self.menubar)

        self.title("RGKit Robot Comparison")
        self.protocol('WM_DELETE_WINDOW', self.close)

        gs = gridspec.GridSpec(1, 3)
        self.fig = plt.figure(figsize=(15, 5))

        self.ax = self.fig.add_subplot(gs[0, :-1])
        self.ax2 = self.fig.add_subplot(gs[0, -1])

        gs.tight_layout(self.fig, rect=[.05, .05, .95, .95])
        self.lines = [None, None]
        self.avglines = [None, None]

        #P1  P2  draw
        self.player_colors = ["b", "r", "w"]
        for i, l in enumerate(self.lines):
            self.lines[i], = self.ax.plot([], [], marker="x", color=self.player_colors[i], label=str(i))
            self.avglines[i] = self.ax.axhspan(0, 0)
        self.ax2.plot(range(-1, 100), range(-1, 100), color="w")

        self.ax.legend()
        self.ax.set_ylabel("Score")
        self.ax.set_xlabel("Round")
        self.ax2.set_title("Score heatmap\n")
        self.scatgrid = np.zeros((19 * 19, 19 * 19))

        cmap = mpl.cm.get_cmap('jet')
        cmaplist = [cmap(i) for i in range(int(cmap.N * 0.8))]
        self.cmap = cmap.from_list('Custom cmap', cmaplist, cmap.N)

        self.cmap.set_under("k")
        self.cmap.set_bad("k")
        self.norm = colors.LogNorm(1, 2)
        self.scat = self.ax2.imshow(self.scatgrid, interpolation="nearest", norm=self.norm, cmap=self.cmap)
        self.scatcb = self.fig.colorbar(self.scat)
        self.axcb = self.scatcb.ax

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        self.canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

    def run(self):
        self.target_samples += self.run_samples
        for i in range(self.run_samples):
            self.task_queue.put((i, [p.fname for p in self.players], self.map_fname, self.turns))

        for i, p in enumerate(self.processes):
            if p is None:
                self.processes[i] = multiprocessing.Process(name="Worker process " + str(i), target=comparison_worker,
                                                            args=(i, self.task_queue, self.done_queue))

        if self.show:
            self.menubar.entryconfigure('Run', state=Tk.DISABLED)
        self.running = True

        print "Launching comparison in", len(self.processes), "threads."
        for p in self.processes:
            if not p.is_alive():
                p.start()

        self.check_done_queue()

    def check_done_queue(self):
        try:
            if self.tasks_finished < self.target_samples:
                self.after(50, self.check_done_queue)
                try:
                    result, runtime = self.done_queue.get(False)
                except Queue.Empty as e:
                    return
                self.tasks_finished += 1
                winner = np.argmax(result) if result[0] != result[1] else -1

                self.winners.append(winner)
                self.results.append(result)
                self.runtimes.append(runtime)

                print ("\r" + " " * 100 +
                       "\rResult {0}/{1}".format(self.tasks_finished, self.target_samples) +
                       " (took %1.1fs):" % runtime).ljust(30), \
                    str(self.players[0]) + " " + str(result[0]) + " : " + str(result[1]) + " " + str(self.players[1])

                print (("Results so far: {0} {1}:{2} {3} (time per game: {4:.3}" + pm + "{5:.2}s)").format(
                    str(self.players[0]), self.winners.count(0), self.winners.count(1), str(self.players[1]),
                    np.average(self.runtimes), np.std(self.runtimes)))
                sys.stdout.flush()

                if self.show:
                    self.ax.axvspan(self.tasks_finished - 1.5, self.tasks_finished - 0.5,
                                    color=self.player_colors[winner], alpha=0.3)

                    self.scatgrid[tuple(result)] += 1

                    if self.done_queue.empty():
                        self.update()
            else:
                self.running = False
                print "\n",
                if self.show:
                    self.menubar.entryconfigure('Run', state=Tk.NORMAL)
                return

        except KeyboardInterrupt:
            print "kbd interrupt"
            self.abort()

    def update(self):
        r = np.array(self.results)
        maxr = np.max(r)

        self.ax.set_xlim([-0.5, self.tasks_finished - 0.5])
        self.ax.set_ylim([0, maxr])
        self.ax2.set_xlim([-.5, maxr + 0.5])
        self.ax2.set_ylim([-.5, maxr + 0.5])

        avg = np.average(r, axis=0)
        std = np.std(r, axis=0)

        self.ax.set_title("{0} {1}:{2} {3}".format(str(self.players[0]), self.winners.count(0), self.winners.count(1),
                                                   str(self.players[1])))
        for i, l in enumerate(self.lines):
            self.lines[i].set_xdata(range(len(r)))
            self.lines[i].set_ydata(r[:, i])

            self.avglines[i].remove()
            self.avglines[i] = self.ax.axhspan(avg[i] - std[i], avg[i] + std[i], color=self.player_colors[i],
                                               alpha=0.15)

        #redraw whole scatter plot every turn (the commented out code below
        # doesn't seem to work)
        #self.scat.set_data(self.scatgrid)

        self.axcb.cla()  # clear colourbar axes
        self.scat.remove()
        self.norm = colors.LogNorm(1, np.max(self.scatgrid))
        self.scat = self.ax2.imshow(self.scatgrid, interpolation="nearest", norm=self.norm, cmap=self.cmap)
        self.scatcb = mpl.colorbar.ColorbarBase(self.axcb, cmap=self.cmap, norm=self.norm, extend="min",
                                                ticks=np.arange(1, 1 + np.max(self.scatgrid)))
        self.scatcb.set_ticklabels(np.arange(1, 1 + np.max(self.scatgrid)))
        self.ax2.set_title("Score heatmap\nAverage: " + str(int(round(avg[0]))) + " : " + str(int(round(avg[1]))))

        self.canvas.draw()
        #TODO: use blit for faster drawing
        #for l,ax,bg in zip(self.lines,self.fig.axes,self.backgrounds):
        #    self.fig.canvas.restore_region(bg)
        #    ax.draw_artist(l)
        #    self.fig.canvas.blit(ax.bbox)

    def batch_test(self, fnames):
        #test all bots against each other
        #save plot for each
        pass

    def open_robot(self):
        new_fnames = tkFileDialog.askopenfilenames(filetypes=[("Python source", ".py")])
        print "New robots", new_fnames

        #Replace a single bot
        if len(new_fnames) == 1:
            old_player_fnames = self.players.fnames()

            RCReplaceDialog(self, new_fnames[0])

            if self.players.fnames() != old_player_fnames:
                self.initialize()

        #Replace both bots
        if len(new_fnames) == 2:
            print "Replacing both bots..."
            print "players before:", str(self.players)
            self.players = PlayerList(self, new_fnames)
            print "players after:", str(self.players)
            self.initialize()

        #Batch test multiple bots
        elif len(new_fnames) > 2:
            self.batch_test(new_fnames)


    def clear(self):
        #clear all plots to make way for a new comparison
        pass

    def close(self):
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            print "Attempting to quit."
            self.abort()
            
    def abort(self):
        print "ABANDON SHIP!"
        for p in self.processes:
            if p is not None and p.is_alive():
                p.terminate()
        if self.show:
            self.quit()
            self.destroy()  # prevent Fatal Python Error: PyEval_RestoreThread: NULL tstate

    def save_plot(self, fname=None):
        if fname is None or not os.path.exists(os.path.dirname(fname)):
            default_save_fname = "_vs_".join(self.players.names()) + ".png"
            fname = tkFileDialog.asksaveasfilename(
                filetypes=[("PNG", ".png"), ("JPEG", ".jpg"), ("SVG", ".svg"), ("PDF", ".pdf")],
                defaultextension=".png", initialfile=default_save_fname)
        self.fig.savefig(fname)

    def upload_imgur(self):
        if tkMessageBox.askokcancel("Continue?", "This will open a link in the browser"):
            with tempfile.TemporaryFile(suffix=".png") as tmpfile:  # doesn't work

                self.fig.savefig(tmpfile, format="png")
                tmpfile.seek(0)
                imgenc = b64encode(tmpfile.read())

                headers = {"Authorization": "Client-ID {0}".format(client_id)}
                url = "https://api.imgur.com/3/upload.json"
                req = urllib2.Request(url, headers=headers, data=urllib.urlencode(
                    {'key': client_id, 'image': imgenc, 'type': 'base64', 'title': " vs ".join(self.players.names())}))

                print urllib.urlencode({'key': client_id, 'image': b64encode(tmpfile.read()), 'type': 'base64',
                                        'title': " vs ".join(self.players.names())})
                try:
                    res = urllib2.urlopen(req)
                    data = json.loads(res.read())

                    if data['success']:
                        print "Opening link:", data['data']['link']
                        print "Delete Hash:", data['data'][
                            'deletehash'], "(save this, if you want to delete the image later)"
                        webbrowser.open(data['data']['link'])
                    else:
                        print "There was an error:", data

                except urllib2.HTTPError as e:
                    print "HTTP Error", e.code, ":", e.reason


def main():
    multiprocessing.freeze_support()
    import argparse

    parser = argparse.ArgumentParser(prog='rgcompare',
                                     description='Compare two or more robotgame controller bots in rgkit')
    parser.add_argument('robots', metavar='r', nargs="*",
                        help='robots to fight each other. not yet implemented: if more than two, batch mode will '
                             'commence')
    parser.add_argument('--initrun', action='store_true', help='attempt to run game as soon as launched')
    parser.add_argument('--games', action='store', help='number of games to run (default 100)', default=100, type=int)
    parser.add_argument('--turns', action='store', default=100, type=int,
                        help='number of turns per run to set (default 100)')
    parser.add_argument('--version', action='version', version='%(prog)s {0}'.format(version))
    parser.add_argument('--processes', action='store',
                        help='number of processors to use for calculation (default NUM_PROCESSORS)', default=0,
                        type=int)
    parser.add_argument('--batch', metavar='output dir', nargs="?", default=0, action='store',
                        help='not yet implemented: and save image of every battle when finished (default: rgcompare/)')
    parser.add_argument('--no-gui', action='store_true', help='run without graphics (enables initial run)')
    parser.add_argument('--map', action='store', help='map to use (default maps/default.py)', default='maps/default.py')

    args = parser.parse_args()

    player_fnames = []
    if args.robots is not None:
        for fname in args.robots:
            if os.path.isfile(fname):
                player_fnames.append(fname)

    if args.batch != 0 and len(player_fnames) < 2:
        print "Please specify enough robots or use GUI"
        sys.exit()
    elif args.batch != 0 or len(player_fnames) > 2:
        print "Sorry, batch mode not yet implemented."
        sys.exit()

    if not args.initrun and args.no_gui:
        args.initrun = True

    map_fname = os.path.join(os.path.dirname(rg.__file__), args.map)

    print "Running with args", args
    c = RobotComparison(None, map_fname, player_fnames=args.robots, samples=args.games, turns=args.turns,
                        processes=args.processes, initrun=args.initrun, batch=args.batch, show=not args.no_gui)


if __name__ == "__main__":
    main()
