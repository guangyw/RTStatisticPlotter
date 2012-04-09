"""
It allows "live" plotting as well as manual zooming to specific
regions.

Both X and Y axes allow "auto" or "manual" settings. For Y, auto
mode sets the scaling of the graph to see all the data points.
For X, auto mode makes the graph "follow" the data. Set it X min
to manual 0 to always see the whole data from the beginning.

Note: press Enter in the 'manual' text box to make a new value 
affect the plot.

This code is modified by Guangyan Wang from Eli Bendersky's work(eliben@gmail.com)
License: this code is in the public domain
"""
import os
import pprint
import random
import sys
import wx
import threading

import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import matplotlib.pyplot as plt

import time

from twisted.internet import reactor

class DataGen(object):
    """ Fetch data from shared memory dataToDisplay
    """
    dataToDisplay = {}
    def __init__(self, dataToDisplay, index, init=0):
        self.data = self.init = init
        self.dataToDisplay = dataToDisplay
        self.index = index
        
    def next(self):
		#print self.dataToDisplay;
		self.keys = self.dataToDisplay.keys()
		if (str(self.index) in self.keys):
			self.data = self.dataToDisplay.get(str(self.index))
			print self.data
			return self.data
		else:
			return 0

class StaticsBox(wx.Panel):
	"""A static box to display statics of the stream, like average, sum...
	"""
	data = []
	def __init__(self, parent, ID, label, initval, data):
		wx.Panel.__init__(self, parent, ID)
		self.data.append(data)
		
		self.value = initval
		box = wx.StaticBox(self, -1, label)
		sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
		self.static_string_ave = wx.StaticText(self, -1, size=(35,-1), label='ave', style=wx.TE_PROCESS_ENTER)
		self.static_string_min = wx.StaticText(self, -1, size=(35,-1), label='min', style=wx.TE_PROCESS_ENTER)
		self.static_string_max = wx.StaticText(self, -1, size=(35,-1), label='max', style=wx.TE_PROCESS_ENTER)
		
		self.static_text_ave = wx.StaticText(self, -1, size=(35,-1), label=str(initval), style=wx.TE_PROCESS_ENTER)
		self.static_text_min = wx.StaticText(self, -1, size=(35,-1), label=str(initval), style=wx.TE_PROCESS_ENTER)
		self.static_text_max = wx.StaticText(self, -1, size=(35,-1), label=str(initval), style=wx.TE_PROCESS_ENTER)
				
		text_ave_box = wx.BoxSizer(wx.HORIZONTAL)
		text_min_box = wx.BoxSizer(wx.HORIZONTAL)
		text_max_box = wx.BoxSizer(wx.HORIZONTAL)
		
		text_ave_box.Add(self.static_string_ave, flag=wx.ALIGN_CENTER_VERTICAL)
		text_ave_box.AddSpacer(15)
		text_ave_box.Add(self.static_text_ave, flag=wx.ALIGN_CENTER_VERTICAL)
		text_min_box.Add(self.static_string_min, flag=wx.ALIGN_CENTER_VERTICAL)
		text_min_box.AddSpacer(15)
		text_min_box.Add(self.static_text_min, flag=wx.ALIGN_CENTER_VERTICAL)
		text_max_box.Add(self.static_string_max, flag=wx.ALIGN_CENTER_VERTICAL)
		text_max_box.AddSpacer(15)
		text_max_box.Add(self.static_text_max, flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(text_ave_box, 0, wx.ALL, 10)
		sizer.Add(text_min_box, 0, wx.ALL, 10)
		sizer.Add(text_max_box, 0, wx.ALL, 10)
		self.SetSizer(sizer)
		sizer.Fit(self)
		self.redraw_timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
		self.redraw_timer.Start(100)
	def on_redraw_timer(self, event):
		pass
		

class BoundControlBox(wx.Panel):
    """ A static box with a couple of radio buttons and a text
        box. Allows to switch between an automatic mode and a 
        manual mode with an associated value.
    """
    def __init__(self, parent, ID, label, initval):
        wx.Panel.__init__(self, parent, ID)
        
        self.value = initval
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        self.radio_auto = wx.RadioButton(self, -1, 
            label="Auto", style=wx.RB_GROUP)
        self.radio_manual = wx.RadioButton(self, -1,
            label="Manual")
        self.manual_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER)
        
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.manual_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.manual_text)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.radio_manual, flag=wx.ALIGN_CENTER_VERTICAL)
        manual_box.Add(self.manual_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(self.radio_auto, 0, wx.ALL, 10)
        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.value = self.manual_text.GetValue()
    
    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def manual_value(self):
        return self.value


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Realtime Statics Plotter'
    
    def __init__(self, dataToDisplay, index, addr):
        wx.Frame.__init__(self, None, -1, self.title)
        
        self.index = index
        self.addr = addr
        self.datagen = DataGen(dataToDisplay, index, 0)
        self.data = [self.datagen.next()]        
        self.ave = float(self.data[0])
        self.data_total = self.ave
        self.min = self.ave
        self.max = self.ave
        #print self.data
        self.paused = False
        
        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(200)

    def create_menu(self):
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
                
        self.menubar.Append(menu_file, "&File")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)

        self.xmin_control = BoundControlBox(self.panel, -1, "X min", 0)
        self.xmax_control = BoundControlBox(self.panel, -1, "X max", 50)
        self.ymin_control = BoundControlBox(self.panel, -1, "Y min", 0)
        self.ymax_control = BoundControlBox(self.panel, -1, "Y max", 100)
        
        self.statics_display = StaticsBox(self.panel, -1, "Static Values", 0, self.data)
        
        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
        
        self.cb_grid = wx.CheckBox(self.panel, -1, 
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)
        
        self.cb_xlab = wx.CheckBox(self.panel, -1, 
            "Show X labels",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_xlab, self.cb_xlab)        
        self.cb_xlab.SetValue(True)
        
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(20)
        self.hbox1.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(10)
        self.hbox1.Add(self.cb_xlab, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        
        self.hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox2.Add(self.xmin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.xmax_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.ymin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.ymax_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.statics_display, border=5, flag=wx.ALL)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        self.vbox.Add(self.hbox2, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        
        DataCursor(self.plot_data)
       
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
    
    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('white')
        self.axes.set_title('Data from client %s' % self.addr, size=12)
        
        plt.setp(self.axes.get_xticklabels(), fontsize=8)
        plt.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data = self.axes.plot(
            self.data[0], 
            linewidth=1,
            color=(0, 0, 0),
            )[0]

    def draw_plot(self):
        """ Redraws the plot
        """
        # when xmin is on auto, it "follows" xmax to produce a 
        # sliding window effect. therefore, xmin is assigned after
        # xmax.
        #
        if self.xmax_control.is_auto():
            xmax = len(self.data) if len(self.data) > 50 else 50
        else:
            xmax = int(self.xmax_control.manual_value())
        if self.xmin_control.is_auto():            
            xmin = xmax - 50
        else:
            xmin = int(self.xmin_control.manual_value())

        # for ymin and ymax, find the minimal and maximal values
        # in the data set and add a mininal margin.
        # 
        # note that it's easy to change this scheme to the 
        # minimal/maximal value in the current display, and not
        # the whole data set.
        # 
        if self.ymin_control.is_auto():
            ymin = round(min(self.data), 0) - 1
        else:
            ymin = int(self.ymin_control.manual_value())
        
        if self.ymax_control.is_auto():
            ymax = round(max(self.data), 0) + 1
        else:
            ymax = int(self.ymax_control.manual_value())

        self.axes.set_xbound(lower=xmin, upper=xmax)
        self.axes.set_ybound(lower=ymin, upper=ymax)
        
        # anecdote: axes.grid assumes b=True if any other flag is
        # given even if b is set to False.
        # so just passing the flag into the first statement won't
        # work.
        #
        if self.cb_grid.IsChecked():
            self.axes.grid(True, color='gray')
        else:
            self.axes.grid(False)

        # Using setp here is convenient, because get_xticklabels
        # returns a list over which one needs to explicitly 
        # iterate, and setp already handles this.
        #  
        plt.setp(self.axes.get_xticklabels(), 
            visible=self.cb_xlab.IsChecked())
        
        self.plot_data.set_xdata(np.arange(len(self.data)))
        self.plot_data.set_ydata(np.array(self.data))
        
        self.statics_display.static_text_ave.SetLabel(str(self.ave))
        self.statics_display.static_text_min.SetLabel(str(self.min))
        self.statics_display.static_text_max.SetLabel(str(self.max))
        #DataCursor(self.plot_data)
        
        self.canvas.draw()
    
    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)
    
    def on_cb_grid(self, event):
        self.draw_plot()
    
    def on_cb_xlab(self, event):
        self.draw_plot()
    
    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(
            self, 
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)
    
    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        #
        if not self.paused:
			self.data_next = float(self.datagen.next())
			self.data.append(self.data_next)
			self.data_total = self.data_total + self.data_next
			self.ave = self.data_total/len(self.data)
			if (self.data_next<self.min):
				self.min = self.data_next
			if (self.data_next>self.max):
				self.max = self.data_next
			self.draw_plot()
    
    def on_exit(self, event):
        self.Destroy()
    
    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, 
            self.on_flash_status_off, 
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
	def on_flash_status_off(self, event):
		self.statusbar.SetStatusText('')
        
from matplotlib import cbook

class DataCursor(object):
    """A simple data cursor widget that displays the x,y location of a
    matplotlib artist when it is selected."""
    def __init__(self, artists, tolerance=5, offsets=(-20, 20), 
                 template='x: %0.2f\ny: %0.2f', display_all=False):
        """Create the data cursor and connect it to the relevant figure.
        "artists" is the matplotlib artist or sequence of artists that will be 
            selected. 
        "tolerance" is the radius (in points) that the mouse click must be
            within to select the artist.
        "offsets" is a tuple of (x,y) offsets in points from the selected
            point to the displayed annotation box
        "template" is the format string to be used. Note: For compatibility
            with older versions of python, this uses the old-style (%) 
            formatting specification.
        "display_all" controls whether more than one annotation box will
            be shown if there are multiple axes.  Only one will be shown
            per-axis, regardless. 
        """
        self.template = template
        self.offsets = offsets
        self.display_all = display_all
        if not cbook.iterable(artists):
            artists = [artists]
        self.artists = artists
        self.axes = tuple(set(art.axes for art in self.artists))
        self.figures = tuple(set(ax.figure for ax in self.axes))

        self.annotations = {}
        for ax in self.axes:
            self.annotations[ax] = self.annotate(ax)

        for artist in self.artists:
            artist.set_picker(tolerance)
        for fig in self.figures:
            fig.canvas.mpl_connect('pick_event', self)

    def annotate(self, ax):
        """Draws and hides the annotation box for the given axis "ax"."""
        annotation = ax.annotate(self.template, xy=(0, 0), ha='right',
                xytext=self.offsets, textcoords='offset points', va='bottom',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
                )
        annotation.set_visible(False)
        return annotation

    def __call__(self, event):
        """Intended to be called through "mpl_connect"."""
        # Rather than trying to interpolate, just display the clicked coords
        # This will only be called if it's within "tolerance", anyway.
        x, y = event.mouseevent.xdata, event.mouseevent.ydata
        annotation = self.annotations[event.artist.axes]
        if x is not None:
            #if not self.display_all:
                # Hide any other annotation boxes...
            #    for ann in self.annotations.values():
            #        ann.set_visible(False)
            # Update the annotation in the current axis..
            annotation.xy = x, y
            annotation.set_text(self.template % (x, y))
            annotation.set_visible(True)
            #event.canvas.draw()

	
#def startPlotting(dataToDisplay):
def startPlotting(*args):
	dataToDisplay = args[0]
	addr = args[2]
	index = args[1]
	app = wx.PySimpleApp()
	app.frame = GraphFrame(dataToDisplay, index, addr)
	app.frame.Show()
	app.MainLoop()
	

