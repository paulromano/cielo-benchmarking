#!/usr/bin/env python3

import sys
from math import sqrt
from collections import OrderedDict
import os
from fnmatch import fnmatch
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import Tk

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import scipy.stats
import xlrd

sys.path.insert(0, '/home/romano/benchmarks/icsbep')
from icsbep.icsbep import model_keff


def get_input(files):
    os.system('clear')
    print("""
1) Add file
2) Set plot options
3) Set file options
4) Plot (save file)
5) Plot (show)
6) Exit

Files:""")
    for filename in files:
        print('  ' + filename)
    print('')
    return eval(input('--> '))

def add_file():
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=(("Spreadsheets", "*.xls*"),
                                          ("All", "*.*")))
    root.destroy()
    label = input('Enter label: ')
    return label, filename

def set_options(options):
    choice = None
    while choice != 10:
        os.system('clear')
        print("""
1) Plot type                                     [{plot_type}]
2) Show shaded uncertainties around mean         [{show_shaded}]
3) Show error bars on individual cases           [{show_uncertainties}]
4) Show legend                                   [{show_legend}]
5) Case name pattern match                       [{match}]
6) Title                                         [{title}]
7) Author                                        [{author}]
8) X-axis label                                  [{xlabel}]
9) Y-axis label                                  [{ylabel}]
10) Return to main menu
""".format(**options))
        choice = eval(input('--> '))
        if choice == 1:
            options['plot_type'] = input('Enter plot type [keff/diff]: ')
        elif choice == 2:
            options['show_shaded'] = not options['show_shaded']
        elif choice == 3:
            options['show_uncertainties'] = not options['show_uncertainties']
        elif choice == 4:
            options['show_legend'] = not options['show_legend']
        elif choice == 5:
            options['match'] = input('Enter matching pattern: ')
        elif choice == 6:
            options['title'] = input('Enter title: ')
        elif choice == 7:
            options['author'] = input('Enter author: ')
        elif choice == 8:
            options['xlabel'] = input('Enter x-label: ')
        elif choice == 9:
            options['ylabel'] = input('Enter y-label: ')

def set_file_main(options):
    n = len(options['files'])
    choice = None
    while choice != n + 1:
        os.system('clear')
        print("Select file:")
        for i, filename in enumerate(options['files']):
            print("{}) {}".format(i + 1, filename))
        print("{}) Return to main menu".format(len(options['files']) + 1))
        choice = eval(input('--> '))
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
        choice = eval(input('--> '))
        if choice == 1:
            options['labels'][i] = input('Enter label: ')

def plot(options, save=False):
    # Read data from files
    labels = OrderedDict()
    x = []
    coe = []
    stdev = []
    count = 0
    benchmark_list = []
    for xls in options['files']:
        book = xlrd.open_workbook(xls)
        sheet = book.sheet_by_index(0)

        x.append([])
        coe.append([])
        stdev.append([])
        for i in range(sheet.nrows - 1):
            words = sheet.cell(i, 0).value.split('/')
            model = words[1]
            volume, form, spectrum, number = model.split('-')
            abbreviation = volume[0] + form[0] + spectrum[0]

            if len(words) >= 4:
                benchmark = model + '/' + words[3]
                case = words[3].replace('case', '')
            else:
                benchmark = model
                case = ''
            name = '{}{}{}'.format(abbreviation, int(number), case)

            if options['match']:
                if not fnmatch(benchmark, options['match']):
                    continue

            if name in labels:
                count = labels[name]
            else:
                count += 1
                labels[name] = count
                benchmark_list.append(benchmark)

            if benchmark in model_keff:
                experiment = model_keff[benchmark][0]
            else:
                experiment = 1.0

            x[-1].append(count)
            coe[-1].append(sheet.cell(i, 1).value/experiment)
            stdev[-1].append(1.96 * sheet.cell(i, 2).value)

    # Get pretty color map
    n = len(labels)

    # Plot data
    if options['plot_type'] == 'keff':
        for i in range(len(x)):
            mu = sum(coe[i])/len(coe[i])
            sigma = sqrt(sum([s**2 for s in stdev[i]]))/len(stdev[i])

            kwargs = {'color': f'C{i}', 'mec': 'black', 'mew': 0.15}
            if options['show_legend']:
                kwargs['label'] = options['labels'][i] + '\nAverage C/E = {:.4f}'.format(mu)

            if options['show_uncertainties']:
                plt.errorbar(x[i], coe[i], yerr=stdev[i], fmt='o', **kwargs)
            else:
                plt.plot(x[i], coe[i], 'o', **kwargs)


            if options['show_shaded']:
                ax = plt.gca()
                verts = [(0, mu - sigma), (0, mu + sigma), (n+1, mu + sigma), (n+1, mu - sigma)]
                poly = Polygon(verts, facecolor=f'C{i}', alpha=0.5)
                ax.add_patch(poly)
            else:
                plt.plot([-1,n], [mu, mu], '-', color=f'C{i}', lw=1.5)

        # Show shaded region of benchmark model uncertainties
        uncverts = []
        for i, benchmark in enumerate(benchmark_list):
            unc = 0.0 if benchmark not in model_keff else model_keff[benchmark][1]
            uncverts.append((1 + i, 1 + unc))
        for i, benchmark in enumerate(benchmark_list[::-1]):
            unc = 0.0 if benchmark not in model_keff else model_keff[benchmark][1]
            uncverts.append((n - i, 1 - unc))
        poly = Polygon(uncverts, facecolor='gray', edgecolor=None, alpha=0.2)
        ax = plt.gca()
        ax.add_patch(poly)

        # Configure plot
        ax = plt.gca()
        plt.xticks(range(1,n+1), labels.keys(), rotation='vertical')
        plt.xlim((0,n+1))
        plt.subplots_adjust(bottom=0.15)
        plt.setp(ax.get_xticklabels(), fontsize=10)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        plt.gcf().set_size_inches(17,6)

    elif options['plot_type'] == 'diff':
        kwargs = {'mec': 'black', 'mew': 0.15}

        coe0 = np.array(coe[0])
        stdev0 = np.array(stdev[0])
        for i, coe in enumerate(coe[1:]):
            coe = np.array(coe)
            stdev_ = np.array(stdev[i + 1])
            err = abs(coe/coe0)*np.sqrt((stdev_/coe)**2 + (stdev0/coe)**2)
            if options['show_uncertainties']:
                plt.errorbar(x[0], coe - coe0, yerr=err, fmt='o',
                             label=options['labels'][i + 1], color=f'C{i}', **kwargs)
            else:
                plt.plot(x[0], coe - coe0, 'o', label=options['labels'][i + 1],
                         color=f'C{i}', **kwargs)

            mu = sum(coe - coe0)/len(coe0)
            if options['show_shaded']:
                sigma = sqrt(sum([s**2 for s in err]))/len(err)
                ax = plt.gca()
                verts = [(0, mu - sigma), (0, mu + sigma), (n+1, mu + sigma), (n+1, mu - sigma)]
                poly = Polygon(verts, facecolor=f'C{i}', alpha=0.5)
                ax.add_patch(poly)
            else:
                plt.plot([-1,n], [mu, mu], '-', color=f'C{i}', lw=1.5)

        # Configure plot
        ax = plt.gca()
        plt.xticks(range(1,n+1), labels.keys(), rotation='vertical')
        plt.xlim((0,n+1))
        plt.subplots_adjust(bottom=0.15)
        plt.setp(ax.get_xticklabels(), fontsize=10)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        plt.gcf().set_size_inches(17,6)

    plt.xlabel(options['xlabel'], fontsize=18)
    plt.ylabel(options['ylabel'], fontsize=18)
    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)
    if options['title']:
        plt.title(options['title'], multialignment='left')
    if options['show_legend']:
        lgd = plt.legend(loc='center left', bbox_to_anchor=(1.0,0.5), numpoints=1)
    else:
        lgd = None

    if save:
        # Get file name
        root = Tk()
        root.withdraw()
        filename = asksaveasfilename()
        root.destroy()
        plt.savefig(filename, bbox_extra_artists=(lgd,), bbox_inches='tight')
    else:
        plt.show()
    plt.close()

if __name__ == "__main__":
    options = {'files': [],
               'labels': [],
               'plot_type': 'keff',
               'show_shaded': True,
               'show_uncertainties': False,
               'show_legend': True,
               'xlabel': 'Benchmark case',
               'ylabel': r'$k_{\mathrm{eff}}$ C/E',
               'match': '',
               'title': '',
               'author': 'Paul Romano'}

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
