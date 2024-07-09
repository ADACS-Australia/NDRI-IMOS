import numpy
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider


plt.ion()
plots = []


# Zoom functionality using the scroll wheel
def zoom(event):
    cur_xlim = ax.get_xlim()
    cur_ylim = ax.get_ylim()
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

    ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * relx])
    ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * rely])
    plt.draw()


def plot1D(y: numpy.ndarray, xlim: int):
    x = numpy.arange(len(y))

    fig, ax = plt.subplots()

    line, = ax.plot(x, y)

    # Set initial view limits
    if xlim is None:
        ax.set_xlim(0, len(y))
    else:
        ax.set_xlim(0, xlim)
    ax.set_ylim(min(y), max(y))

    fig.canvas.mpl_connect('scroll_event', zoom)

    ax.set_xlabel('Index')
    ax.set_ylabel('Value')
    ax.set_title('1D Array Plot')

    # Show the plot
    plt.show(block=True)
