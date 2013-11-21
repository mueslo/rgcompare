#import system stuff
import sys,time,os
from multiprocessing import Process, Queue, freeze_support, cpu_count


#import GUI stuff
import Tkinter as Tk
import tkMessageBox,tkFileDialog#,tkSimpleDialog

#import plotting stuff
import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import colors
import numpy as np

#import RG stuff
import game
import ast
from settings import settings


class RedirectStdStreams(object):
    def __init__(self, stdout=None, stderr=None):
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush(); self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        self._stdout.flush(); self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


class RCReplaceDialog(Tk.Toplevel):
    def __init__(self, parent, fname):
        Tk.Toplevel.__init__(self,parent)
        self.parent = parent
        self.transient(parent)

        Tk.Label(self, text="Which robot would you like to replace with {0}?".format(os.path.basename(fname))).pack()
        Tk.Button(self, text=str(parent.player_fnames[0]), command=self.p1).pack(side=Tk.LEFT)
        Tk.Button(self, text=str(parent.player_fnames[1]), command=self.p2).pack(side=Tk.RIGHT)
        self.wait_window()

    def p1(self):
        #todo: better communication between dialog and mainwin
        self.parent.receive(0)
        self.destroy()
    def p2(self):
        self.parent.receive(1)
        self.destroy()

'''
class RCSettingsDialog(tkSimpleDialog.Dialog):
    def body(self, master):
        self.title("Settings")

        Tk.Label(master, text="Runs:").grid(row=0)
        Tk.Label(master, text="Turns per run:").grid(row=1)

        self.e1 = Tk.Entry(master)
        self.e2 = Tk.Entry(master)

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)

        return self.e1 # initial focus

    def apply(self):
        first = int(self.e1.get())
        second = int(self.e2.get())
        print first, second # or something
'''

def comparison_worker(self,input, output):
    devnull = open(os.devnull, 'w')
    try:
        with RedirectStdStreams(stdout=devnull, stderr=devnull):
            for match_id,player_fnames, map_fname, turns in iter(input.get, 'STOP'):

                map_data = ast.literal_eval(open(map_fname).read())
                game.init_settings(map_data)
                players = [game.Player(open(x).read()) for x in player_fnames]
                g = game.Game(*players, record_turns=False)

                t_start = time.time()
                for i in range(turns):
                    print (' running turn %d '%(g.turns)).center(70, '-')
                    g.run_turn()
                t_end = time.time()

                output.put([g.get_scores(),t_end-t_start])
    finally:
        print "Terminating worker..."

class RobotComparison(Tk.Tk):

    def __init__(self,parent,map_fname,player_fnames=[None, None],processes=0, samples=100,\
                turns=0,initrun=False,batch=False, show=True):
        #Figure.__init__(self)
        Tk.Tk.__init__(self)
        self.parent = parent

        self.processes=[None]*processes if processes>0 else [None]*cpu_count()

        self.turns=settings.max_turns if turns==0 else turns

        self.player_fnames = player_fnames

        self.player_fnames += (2-len(self.player_fnames))*[None]

        self.map_fname = map_fname

        self.run_samples = samples #num samples per run

        self.setup_UI()
        self.initialize()


        if None in player_fnames:
            self.menubar.entryconfigure('Run',state=Tk.DISABLED)

        try:
            if initrun:
                self.run(ignore=True)
            self.mainloop()
        except KeyboardInterrupt:
            self.abort()
        finally:
            for p in self.processes:
                self.task_queue.put('STOP')

    def initialize(self):
        print "Initialising with players",self.player_fnames
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.tasks_finished = 0
        self.target_samples = 0
        self.running = False
        self.results = []
        self.runtimes = []
        self.winners = []


        if None in player_fnames:
            self.menubar.entryconfigure('Run',state=Tk.DISABLED)
        else:
            self.menubar.entryconfigure('Run',state=Tk.NORMAL)

        #label stuff due to fnames
        for i,f in enumerate(self.player_fnames):
            self.lines[i].set_label(os.path.basename(str(f)))
        self.ax.legend(ncol=2)
        self.ax2.set_ylabel(os.path.basename(str(self.player_fnames[0])))
        self.ax2.set_xlabel(os.path.basename(str(self.player_fnames[1])))
        self.ax.set_title("{0} {1}:{2} {3}".format(os.path.basename(str(self.player_fnames[0])),\
        self.winners.count(0),self.winners.count(1),os.path.basename(str(self.player_fnames[1]))))

        self.canvas.draw()


    def placebo(self):
        pass

    def setup_UI(self):
        #plt.rc('text', usetex=True)
        #plt.rc('font', family='sans-serif')

        import matplotlib.gridspec as gridspec

        self.menubar = Tk.Menu(self)

        self.filemenu = Tk.Menu(self.menubar,tearoff=0)
        self.filemenu.add_command(label="Open robot", command=self.open_robot)
        self.filemenu.add_command(label="Save plot", command=self.save_plot)
        self.menubar.add_cascade(label="File",menu=self.filemenu)
        #self.menubar.add_command(label="Settings", command=self.change_settings)
        self.menubar.add_command(label="Run", command=self.run, state='disabled')
        self.menubar.add_command(label="Quit", command=self.close)
        self.config(menu=self.menubar)

        self.title("RGKit Robot Comparison")
        self.protocol('WM_DELETE_WINDOW', self.close)

        gs = gridspec.GridSpec(1,3)
        self.fig = plt.figure(figsize=(15,5))

        self.ax = self.fig.add_subplot(gs[0,:-1])
        self.ax2 = self.fig.add_subplot(gs[0,-1])

        gs.tight_layout(self.fig,rect=[.05,.05,.95,.95])
        self.lines = [None,None]
        self.avglines = [None,None]
        #self.avglines_lower = [None]*len(player_fnames)

                           #P1  P2  draw
        self.player_colors=["b","r","w"]
        for i,l in enumerate(self.lines):
            self.lines[i], = self.ax.plot([],[],marker="x",color=self.player_colors[i])
            #self.avglines[i], = self.ax.plot([],[],color=self.player_colors[i])
            self.avglines[i] = self.ax.axhspan(0,0)
        self.ax2.plot(range(-1,100),range(-1,100),color="w")
        #self.scat, = self.ax2.plot([],[],ls="",marker="x",color="k")

        #self.resizable(False,False)

        self.ax.legend()
        self.ax.set_ylabel("Score")
        self.ax.set_xlabel("Round")
        self.ax2.set_title("Score heatmap")
        self.scatgrid = np.zeros((19*19,19*19))

        cmap = mpl.cm.get_cmap('jet')
        cmaplist = [cmap(i) for i in range(int(cmap.N*0.8))]
        self.cmap = cmap.from_list('Custom cmap', cmaplist, cmap.N)

        self.cmap.set_under("k")
        self.cmap.set_bad("k")
        self.norm = colors.LogNorm(1,2)
        self.scat = self.ax2.imshow(self.scatgrid,interpolation="nearest",\
                                    norm=self.norm,cmap=self.cmap)
        self.scatcb = self.fig.colorbar(self.scat)
        self.axcb = self.scatcb.ax

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        self.canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)


    def run(self,ignore=False):
        if not ignore and not tkMessageBox.askokcancel("Run?", "This currently blocks user interaction."):
            return


        self.target_samples+=self.run_samples
        for i in range(self.run_samples):

            self.task_queue.put((i,self.player_fnames,map_fname,self.turns))

        for i,p in enumerate(self.processes):
            self.processes[i] = Process(target=comparison_worker, args=(self.task_queue,self.done_queue))


        self.menubar.entryconfigure('Run',state=Tk.DISABLED)
        self.running = True

        print "Launching comparison in",len(self.processes),"threads."
        for p in self.processes:
            if not p.is_alive():
                p.start()
            else:
                print "Thread still alive, no need to start a new one"
        #todo: offload this into another thread.
        #      how would you do this in python without pointers?
        try:
            while self.tasks_finished<self.target_samples:

                result,runtime = self.done_queue.get()

                self.tasks_finished += 1
                print ("Result {0}/{1}".format(self.tasks_finished,\
                    self.target_samples)+" (took %1.1fs):"%(runtime)).ljust(30),\
                    os.path.basename(self.player_fnames[0])+" "+str(result[0])+" : "+\
                    str(result[1])+" "+os.path.basename(self.player_fnames[1])
                winner = np.argmax(result) if result[0]!=result[1] else -1

                self.winners.append(winner)
                self.results.append(result)
                self.runtimes.append(runtime)

                self.ax.axvspan(self.tasks_finished-1.5,self.tasks_finished-0.5,\
                                color=self.player_colors[winner],alpha=0.3)

                self.scatgrid[tuple(result)]+=1
                if self.done_queue.empty():
                    self.update()
                    time.sleep(0.05)
            self.running = False
            self.menubar.entryconfigure('Run',state=Tk.NORMAL)

        except KeyboardInterrupt:
            print "kbd interrupt"
            self.abort()


    def update(self):
        r = np.array(self.results)
        maxr = np.max(r)

        self.ax.set_xlim([-0.5,self.tasks_finished-0.5])
        self.ax.set_ylim([0,maxr])
        self.ax2.set_xlim([-.5,maxr+0.5])
        self.ax2.set_ylim([-.5,maxr+0.5])
        self.ax.set_title("{0} {1}:{2} {3}".format(os.path.basename(str(self.player_fnames[0])),\
        self.winners.count(0),self.winners.count(1),os.path.basename(str(self.player_fnames[1]))))
        for i,l in enumerate(self.lines):
            self.lines[i].set_xdata(range(len(r)))
            self.lines[i].set_ydata(r[:,i])

            avg = np.average(r[:,i])
            std = np.std(r[:,i])
            self.avglines[i].remove()
            self.avglines[i] = self.ax.axhspan(avg-std,avg+std,\
                                            color=self.player_colors[i],alpha=0.15)
            #self.avglines[i].set_xdata([-.5,self.tasks_finished+.5])
            #self.avglines[i].set_ydata(2*[np.average(r[:,i])])

        #redraw whole scatter plot every turn (the commented out code below
        # doesn't seem to work)
        #self.scat.set_data(self.scatgrid)

        self.axcb.cla() #clear colourbar axes
        self.scat.remove()
        self.norm = colors.LogNorm(1,np.max(self.scatgrid))
        self.scat = self.ax2.imshow(self.scatgrid,interpolation="nearest",\
                                    norm=self.norm,cmap=self.cmap)
        self.scatcb = mpl.colorbar.ColorbarBase(self.axcb, cmap=self.cmap, \
                                norm=self.norm, extend="min", \
                                ticks=np.arange(1,1+np.max(self.scatgrid)))
        self.scatcb.set_ticklabels(np.arange(1,1+np.max(self.scatgrid)))



        self.canvas.draw()

    def batch_test(self,fnames):
        #test all bots against each other
        #save plot for each
        pass

    #this is pretty dirty and hacky, but I'm seemingly too dumb to do
    # communication without pointers.
    def receive(self,data):
        print "receiving data:",data
        self.data = data


    def open_robot(self):
        robot_fnames = tkFileDialog.askopenfilenames(filetypes=[("Python source",".py")])
        print "New robots",robot_fnames

        if len(robot_fnames)==1:
            print "Replacing single bot..."

            RCReplaceDialog(self,robot_fnames[0])
            self.player_fnames[self.data]=robot_fnames[0]

            self.initialize()

        if len(robot_fnames)==2:
            print "Replacing both bots..."
            self.player_fnames = list(robot_fnames)
            self.initialize()
        elif len(robot_fnames)>2:
            self.batch_test(robot_fnames)

    #def change_settings(self):
    #    settings = RCSettingsDialog(self)

    def clear(self):
        #clear all plots to make way for a new comparison
        pass

    def close(self):
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            print "Attempting to quit."
            self.quit()

    def abort(self):
        print "ABANDON SHIP!"
        for p in self.processes:
            if p.is_alive() and p is not None:
                p.terminate()
        self.quit()


    def save_plot(self, fname=None):
        if fname is None or not os.path.exists(os.path.dirname(fname)):
            fname = tkFileDialog.asksaveasfilename(filetypes=[("PNG",".png"),("PDF",".pdf")])
        self.fig.savefig(fname)


    #parser.add_argument('--batch')
if __name__ == "__main__":
    freeze_support()
    import argparse

    parser = argparse.ArgumentParser(prog='rgcompare',\
        description='Compare two or more robotgame controller bots in rgkit')
    parser.add_argument('robots', metavar='r',nargs="*",  \
        help='robots to fight each other. not yet implemented: if more than two, batch mode will commence ')
    parser.add_argument('--initrun',action='store_true',\
        help='attempt to run game as soon as launched')
    parser.add_argument('--runs',   action='store',\
        help='number of runs to set (default 100)',default=100,type=int)
    parser.add_argument('--turns',  action='store',default=100,type=int,\
        help='number of turns per run to set (default 100)')
    parser.add_argument('--version',action='version',\
        version='%(prog)s 0.1')
    parser.add_argument('--processes', action='store',\
        help='number of processors to use for calculation \
        (default NUM_PROCESSORS)',default=0,type=int)
    parser.add_argument('--batch', metavar='output dir',nargs="?",\
        default=0,action='store', help='not yet implemented: don\'t create gui, \
        and save image of every battle when finished (default: rgcompare/)')
    parser.add_argument('--map', action='store', \
        help='map to use (default maps/default.py)', default='maps/default.py')


    args = parser.parse_args()

    print "Running with args",args

    player_fnames = []
    if args.robots is not None:
        for fname in args.robots:
            if os.path.isfile(fname):
                player_fnames.append(fname)

    if args.batch!=0 and len(player_fnames)<2:
        print "Please specify enough robots or use GUI"
        sys.exit()
    elif args.batch!=0:
        print "Sorry, batch mode not yet implemented."
        sys.exit()

    map_fname = os.path.join(os.path.dirname(__file__), args.map)


    c = RobotComparison(None,map_fname,player_fnames=args.robots,samples=args.runs,\
                        turns=args.turns,processes=args.processes,\
                        initrun=args.initrun, batch=args.batch)
