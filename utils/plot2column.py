#!/usr/bin/env python

import argparse
import os
from tkFileDialog import askopenfilename, asksaveasfilename
from Tkinter import Tk

import matplotlib.pyplot as plt
import numpy as np


def get_input(files):
    os.system('clear')
    print("""
1) Add file
2) Set plot options
3) Set file options
4) Plot (save file)
5) Plot (show)
6) Exit

Selected files:""")
    for filename in files:
        print('  ' + filename)
    print('')
    return eval(raw_input('Enter selection [1-6]: '))

def add_file():
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=(("All", "*.*"),))
    root.destroy()
    label = raw_input('Enter label for file: ')
    return label, filename

def set_options(options):
    choice = None
    while choice != 10:
        os.system('clear')
        print("""
1) Scale                         [{scale}]
2) Lower limit on x-axis         [{xmin}]
3) Upper limit on x-axis         [{xmax}]
4) Lower limit on y-axis         [{ymin}]
5) Upper limit on y-axis         [{ymax}]
6) Label on x-axis               [{xlabel}]
7) Label on y-axis               [{ylabel}]
8) Show legend                   [{show_legend}]
9) Plot title                    [{title}]
10) Return to main menu
""".format(**options))
        choice = int(raw_input('Enter selection [1-10]: '))
        if choice == 1:
            options['scale'] = raw_input('Enter scale [e.g. log-lin]: ')
        elif choice == 2:
            options['xmin'] = float(raw_input('Lower limit on x-axis: '))
        elif choice == 3:
            options['xmax'] = float(raw_input('Upper limit on y-axis: '))
        elif choice == 4:
            options['ymin'] = float(raw_input('Lower limit on y-axis: '))
        elif choice == 5:
            options['ymax'] = float(raw_input('Upper limit on y-axis: '))
        elif choice == 6:
            options['xlabel'] = raw_input('Label on x-axis: ')
        elif choice == 7:
            options['ylabel'] = raw_input('Label on y-axis: ')
        elif choice == 8:
            options['show_legend'] = eval(raw_input('Show legend? [True/False]: '))
        elif choice == 9:
            options['title'] = raw_input('Enter title: ')

def set_file_main(options):
    n = len(options['files'])
    choice = None
    while choice != n + 1:
        os.system('clear')
        print("Select file:")
        for i, filename in enumerate(options['files']):
            print("{}) {}".format(i + 1, filename))
        print("{}) Return to main menu".format(len(options['files']) + 1))
        choice = eval(raw_input('Enter selection: '))
        if choice != len(options['files']) + 1:
            set_file_options(options, choice - 1)

def set_file_options(options, i):
    choice = None
    while choice != 2:
        os.system('clear')
        print("""
1) File label                                    [{}]
2) Return to file selection
""".format(options['labels'][i]))
        choice = eval(raw_input('Enter selection [1-2]: '))
        if choice == 1:
            options['labels'][i] = raw_input('Enter label: ')

def plot(options, save=False):

    plotfunc = {'lin-lin': plt.plot, 'lin-log': plt.semilogx,
                'log-lin': plt.semilogy, 'log-log': plt.loglog}
    for filename, label in zip(options['files'], options['labels']):
        x, y = np.loadtxt(filename, unpack=True)
        plotfunc[options['scale']](x, y, label=label)

    if options['xmin']: plt.xlim(xmin=options['xmin'])
    if options['xmax']: plt.xlim(xmax=options['xmax'])
    if options['ymin']: plt.ylim(ymin=options['ymin'])
    if options['ymax']: plt.ylim(ymax=options['ymax'])
    if options['xlabel']: plt.xlabel(options['xlabel'])
    if options['ylabel']: plt.ylabel(options['ylabel'])
    if options['title']: plt.title(options['title'])
    if options['show_legend']: plt.legend()

    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)

    if save:
        # Get file name
        root = Tk()
        root.withdraw()
        filename = asksaveasfilename()
        root.destroy()
        plt.savefig(filename, bbox_inches='tight')
    else:
        plt.show()
    plt.close()

if __name__ == "__main__":
    options = {'files': [],
               'labels': [],
               'scale': 'lin-lin',
               'xmin': None,
               'xmax': None,
               'ymin': None,
               'ymax': None,
               'xlabel': '',
               'ylabel': '',
               'show_difference': False,
               'show_legend': True,
               'title': ''}

    while True:
        choice = get_input(options['files'])
        if choice == 1:
            label, filename = add_file()
            if filename:
                options['files'].append(filename)
                options['labels'].append(label)
        elif choice == 2:
            set_options(options)
        elif choice == 3:
            set_file_main(options)
        elif choice == 4:
            plot(options, True)
        elif choice == 5:
            plot(options)
        elif choice == 6:
            break
