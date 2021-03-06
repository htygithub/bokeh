# The plot server must be running
#
# Source of inspiration for example:
# https://www.youtube.com/watch?v=LznjC4Lo7lE

import time

import numpy as np

from bokeh.plotting import figure, show, output_server, curdoc
from bokeh.io import vplot, hplot
from bokeh.models import GlyphRenderer
from bokeh.client import push_session
from bokeh.models.sources import ColumnDataSource as CDS
from collections import OrderedDict

newx = x = np.linspace(0, 2*np.pi, 100)
shift = 2.2
base_x = x + shift

period = np.pi/2.
palette = ['#08519c', '#3182bd', '#6baed6', '#bdd7e7']

def new_source():
    return dict(curve=CDS(), lines=CDS(), circle_point=CDS(), circleds=CDS())

def create_circle_glyphs(p, color, sources):
    p.circle('x', 'y', size=1., line_color=color, color=None, source=sources['circleds'])
    p.circle('x', 'y', size=5, line_color=color, color=color, source=sources['circle_point'])
    p.line('radius_x', 'radius_y', line_color=color, color=color, alpha=0.5, source=sources['lines'])

def create_plot(foos, title='', r = 1, y_range=None, period = np.pi/2., cfoos=None):
    if y_range is None:
        y_range=[-2, 2]

    # create new figure
    p = figure(title=title, width=800, height=300, x_range=[-2.5, 9], y_range=y_range)
    p.xgrid.bounds = (-2, 2)
    p.xaxis.bounds = (-2, 2)

    _sources = []
    cx, cy = 0, 0
    for i, foo in enumerate(foos):
        sources = new_source()
        get_new_sources(x, foo, sources, cfoos[i], cx, cy, i==0)
        cp = sources['circle_point'].data
        cx, cy = cp['x'][0], cp['y'][0]

        if i==0:
            # compute the full fourier eq
            full_y = sum([foo(x) for foo in foos])
            # replace the foo curve with the full fourier eq
            sources['curve'] = CDS(dict(x=x, base_x=base_x, y=full_y))
            # draw the line
            p.line('base_x','y', color="orange", line_width=2, source=sources['curve'],
                    legend="4sin(x)/pi + 4sin(3x)/3pi + 4sin(5x)/5pi + 4sin(7x)/7pi")

        if i==len(foos)-1:
            # if it's the last foo let's draw a circle on the head of the curve
            sources['floating_point'] = CDS({'x':[shift], 'y': [cy]})
            p.line('line_x', 'line_y', color="palette[i]", line_width=2, source=sources['lines'])
            p.circle('x', 'y', size=10, line_color=palette[i], color=palette[i], source=sources['floating_point'])

        # draw the circle, radius and circle point realted to foo domain
        create_circle_glyphs(p, palette[i], sources)
        _sources.append(sources)

    return p, _sources


def get_new_sources(xs, foo, sources, cfoo, cx=0, cy=0, compute_curve = True):
    if compute_curve:
        ys = foo(xs)
        sources['curve'].data = dict(x=xs, base_x=base_x, y=ys)

    r = foo(period)
    y = foo(xs[0]) + cy
    x = cfoo(xs[0]) + cx

    sources['lines'].data = {
        'line_x': [x, shift], 'line_y': [y, y],
        'radius_x': [0, x], 'radius_y': [0, y]
    }
    sources['circle_point'].data = {'x': [x], 'y': [y], 'r': [r]}
    sources['circleds'].data=dict(
        x = cx + np.cos(np.linspace(0, 2*np.pi, 100)) * r,
        y = cy + np.sin(np.linspace(0, 2*np.pi, 100)) * r,
    )


def update_sources(sources, foos, newx, ind, cfoos):
    cx, cy = 0, 0

    for i, foo in enumerate(foos):
        get_new_sources(newx, foo, sources[i], cfoos[i], cx, cy,
                        compute_curve = i != 0)

        if i == 0:
            full_y = sum([foo(newx) for foo in foos])
            sources[i]['curve'].data = dict(x=newx, base_x=base_x, y=full_y)

        cp = sources[i]['circle_point'].data
        cx, cy = cp['x'][0], cp['y'][0]

        if i == len(foos)-1:
            sources[i]['floating_point'].data['x'] = [shift]
            sources[i]['floating_point'].data['y'] = [cy]


def update_centric_sources(sources, foos, newx, ind, cfoos):
    for i, foo in enumerate(foos):
        get_new_sources(newx, foo, sources[i], cfoos[i])


def create_centric_plot(foos, title='', r = 1, y_range=None, period = np.pi/2., cfoos=None):
    if y_range is None:
        y_range=[-2, 2]

    p = figure(title=title, width=800, height=300, x_range=[-1.5, 10.5], y_range=y_range)
    p.xgrid.bounds = (-2, 2)
    p.xaxis.bounds = (-2, 2)

    _sources = []
    for i, foo in enumerate(foos):
        sources = new_source()
        get_new_sources(x, foo, sources, cfoos[i])
        _sources.append(sources)

        if i:
            legend = "4sin(%(c)sx)/%(c)spi" % {'c': i*2+1}
        else:
            legend = "4sin(x)/pi"

        p.line('base_x','y', color=palette[i], line_width=2, source=sources['curve'])
        p.line('line_x', 'line_y', color=palette[i], line_width=2,
                source=sources['lines'], legend=legend)

        create_circle_glyphs(p, palette[i], sources)

    return p, _sources

# Create the series partials..
# NOTE: We could create those dinamically but leaving as
#       is improves readability
f1 = lambda x: (4*np.sin(x))/np.pi
f2 = lambda x: (4*np.sin(3*x))/(3*np.pi)
f3 = lambda x: (4*np.sin(5*x))/(5*np.pi)
f4 = lambda x: (4*np.sin(7*x))/(7*np.pi)
cf1 = lambda x: (4*np.cos(x))/np.pi
cf2 = lambda x: (4*np.cos(3*x))/(3*np.pi)
cf3 = lambda x: (4*np.cos(5*x))/(5*np.pi)
cf4 = lambda x: (4*np.cos(7*x))/(7*np.pi)
fourier = OrderedDict(
    fourier_4 = {
        'f': lambda x: f1(x) + f2(x) + f3(x) + f4(x),
        'fs': [f1, f2, f3, f4],
        'cfs': [cf1, cf2, cf3, cf4]},
)

for k, p in fourier.items():
    p['plot'], p['sources'] = create_plot(
        p['fs'], 'Fourier (Sum of the first 4 Harmonic Circles)', r = p['f'](period), cfoos = p['cfs']
    )

for k, p in fourier.items():
    p['cplot'], p['csources'] = create_centric_plot(
        p['fs'], 'Fourier First 4 Harmonics & Harmonic Circles', r = p['f'](period), cfoos = p['cfs']
    )

# Open a session which will keep our local doc in sync with server
session = push_session(curdoc())
# Open the session in a browser
layout = vplot(*[f['plot'] for f in fourier.values()] + [f['cplot'] for f in fourier.values()])
session.show(layout)

gind = 0
def cb():
    global gind
    global newx
    oldx = np.delete(newx, 0)
    newx = np.hstack([oldx, [oldx[-1] + 2*np.pi/100]])
    gind += 1

    for k, p in fourier.items():
        update_sources(p['sources'], p['fs'], newx, gind, p['cfs'])
        update_centric_sources(p['csources'], p['fs'], newx, gind, p['cfs'])

    if gind >= 99:
        gind = 0

# Add the callback function to the document. This will add the
# callback to the client session main loop (when running the example)
# with bokeh server. The main loop will then call the callback every
# 100 milliseconds.
curdoc().add_periodic_callback(cb, 100)

# Start the session loop
session.loop_until_closed()
