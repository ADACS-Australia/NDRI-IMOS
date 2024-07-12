import numpy
import matplotlib.pyplot as plt
# from matplotlib.widgets import Slider
from matplotlib.widgets import RadioButtons


class DiagnosticPlots:
    def __init__(self):
        self.fig, (self.ax_plot, self.ax_radio) = plt.subplots(1, 2, figsize=(12, 6), 
                                                               gridspec_kw={'width_ratios': [4, 1]})
        self.plots = []
        self.radio = None
        self.y_max = None
        self.fig.suptitle("IMOS Diagnostic Plots")
        # Connect the scroll event to the zoom function
        self.fig.canvas.mpl_connect('scroll_event', self.zoom)

    def add_plot(self, y, title, ymax=None):
        x = numpy.arange(len(y))
        if ymax is not None:
            self.y_max = ymax
        self.plots.append((x, y, title))
        self._update_radio()
        self._show_plot(len(self.plots) - 1)

    def _update_radio(self):
        if self.radio:
            self.ax_radio.clear()
        plot_titles = [diag_plot[2] for diag_plot in self.plots]
        self.radio = RadioButtons(self.ax_radio, plot_titles)
        self.radio.on_clicked(self._radio_clicked)

    def _radio_clicked(self, label):
        index = [plot[2] for plot in self.plots].index(label)
        self._show_plot(index)

    def _show_plot(self, index):
        self.ax_plot.clear()
        x, y, title = self.plots[index]
        if self.y_max is not None:
            self.ax_plot.set_ylim(0, self.y_max)
        self.ax_plot.plot(x, y)
        self.ax_plot.set_title(title)
        self.fig.canvas.draw_idle()

    def show(self):
        plt.show()

    def zoom(self, event):
        # Zoom functionality using the scroll wheel
        if event.inaxes != self.ax_plot:
            return

        cur_xlim = self.ax_plot.get_xlim()
        cur_ylim = self.ax_plot.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        if event.button == 'up':
            scale_factor = 0.9
        elif event.button == 'down':
            scale_factor = 1.1
        else:
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])

        self.ax_plot.set_xlim([xdata - new_width * (1-relx), xdata + new_width * relx])
        self.ax_plot.set_ylim([ydata - new_height * (1-rely), ydata + new_height * rely])
        self.fig.canvas.draw_idle()


# Make the class instance global, using Module-Level Singleton
dp = DiagnosticPlots()
