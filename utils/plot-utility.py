#!/usr/bin/env python

import sys
from math import sqrt
from collections import OrderedDict
import argparse
import os
import time
from fnmatch import fnmatch
from tkFileDialog import askopenfilename, asksaveasfilename
from Tkinter import Tk

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import scipy.stats
import brewer2mpl
import xlrd

from icsbep.icsbep import model_keff

matplotlib.rcParams['ps.useafm'] = True
matplotlib.rcParams['pdf.use14corefonts'] = True
matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['text.latex.preamble'] = ["""
\usepackage[bitstream-charter]{mathdesign}
\usepackage{amsmath}
\usepackage[usenames]{xcolor}
"""]
matplotlib.rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})


def get_input(files):
    os.system('clear')
    print("""
1) Add file
2) Set global options
3) Set file options
4) Plot (save file)
5) Plot (show)
6) Exit

Files:""")
    for filename in files:
        print('  ' + filename)
    print('')
    return eval(raw_input('--> '))

def add_file():
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=(("Spreadsheets", "*.xls*"),
                                          ("All", "*.*")))
    root.destroy()
    label = raw_input('Enter label: ')
    return label, filename

def set_options(options):
    choice = None
    while choice != 8:
        os.system('clear')
        print("""
1) Plot type                                     [{plot_type}]
2) Show shaded uncertainties around mean         [{show_shaded}]
3) Show error bars on individual cases           [{show_uncertainties}]
4) Show legend                                   [{show_legend}]
5) Case name pattern match                       [{match}]
6) Title                                         [{title}]
7) Author                                        [{author}]
8) Return to main menu
""".format(**options))
        choice = eval(raw_input('--> '))
        if choice == 1:
            options['plot_type'] = raw_input('Enter plot type [keff/leakage/diff]: ')
        elif choice == 2:
            options['show_shaded'] = not options['show_shaded']
        elif choice == 3:
            options['show_uncertainties'] = not options['show_uncertainties']
        elif choice == 4:
            options['show_legend'] = not options['show_legend']
        elif choice == 5:
            options['match'] = raw_input('Enter matching pattern: ')
        elif choice == 6:
            options['title'] = raw_input('Enter title: ')
        elif choice == 7:
            options['author'] = raw_input('Enter author: ')

def set_file_main(options):
    n = len(options['files'])
    choice = None
    while choice != n + 1:
        os.system('clear')
        print("Select file:")
        for i, filename in enumerate(options['files']):
            print("{}) {}".format(i + 1, filename))
        print("{}) Return to main menu".format(len(options['files']) + 1))
        choice = eval(raw_input('--> '))
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
        choice = eval(raw_input('--> '))
        if choice == 1:
            options['labels'][i] = raw_input('Enter label: ')

def plot(options, save=False):
    # Read data from files
    labels = OrderedDict()
    x = []
    coe = []
    stdev = []
    leakage = []
    atlf = []
    count = 0
    benchmark_list = []
    for xls in options['files']:
        book = xlrd.open_workbook(xls)
        sheet = book.sheet_by_index(0)

        x.append([])
        coe.append([])
        stdev.append([])
        leakage.append([])
        atlf.append([])
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
            leakage[-1].append(sheet.cell(i, 3).value)
            atlf[-1].append(sheet.cell(i, 5).value)

    # Get pretty color map
    n = len(labels)
    colors = brewer2mpl.get_map('Set2', 'qualitative', max(3,min(8,n))).mpl_colors

    # Plot data
    if options['plot_type'] == 'keff':
        for i in range(len(x)):
            mu = sum(coe[i])/len(coe[i])
            sigma = sqrt(sum([s**2 for s in stdev[i]]))/len(stdev[i])

            kwargs = {'color': colors[i], 'mec': 'black', 'mew': 0.15}
            if options['show_legend']:
                kwargs['label'] = options['labels'][i] + '\nAverage C/E = {:.4f}'.format(mu)

            if options['show_uncertainties']:
                plt.errorbar(x[i], coe[i], yerr=stdev[i], fmt='o', **kwargs)
            else:
                plt.plot(x[i], coe[i], 'o', **kwargs)


            if options['show_shaded']:
                ax = plt.gca()
                verts = [(0, mu - sigma), (0, mu + sigma), (n+1, mu + sigma), (n+1, mu - sigma)]
                poly = Polygon(verts, facecolor=colors[i], alpha=0.5)
                ax.add_patch(poly)
            else:
                plt.plot([-1,n], [mu, mu], '-', color=colors[i], lw=1.5)

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
        plt.xlabel('Benchmark case', fontsize=18)
        plt.ylabel(r'$k_{\text{eff}}$ C/E', fontsize=18)
        plt.gcf().set_size_inches(17,6)

    elif options['plot_type'] == 'diff':
        kwargs = {'mec': 'black', 'mew': 0.15}

        coe0 = np.array(coe[0])
        for i, coe in enumerate(coe[1:]):
            coe = np.array(coe)
            plt.plot(x[0], coe - coe0, 'o', label=options['labels'][i + 1],
                     color=colors[i], **kwargs)

            mu = sum(coe - coe0)/len(coe0)
            plt.plot([-1,n], [mu, mu], '-', color=colors[i], lw=1.5)

        # Configure plot
        ax = plt.gca()
        plt.xticks(range(1,n+1), labels.keys(), rotation='vertical')
        plt.xlim((0,n+1))
        plt.subplots_adjust(bottom=0.15)
        plt.setp(ax.get_xticklabels(), fontsize=10)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        plt.xlabel('Benchmark case', fontsize=18)
        plt.ylabel(r'Difference in $k_{\text{eff}}$ C/E', fontsize=18)
        plt.gcf().set_size_inches(17,6)

    elif options['plot_type'] == 'leakage':
        for i in range(len(x)):
            kwargs = {'color': colors[i], 'mec': 'black', 'mew': 0.15}
            if options['show_legend']:
                kwargs['label'] = options['labels'][i]

            if options['show_uncertainties']:
                plt.errorbar(atlf[i], coe[i], yerr=stdev[i], fmt='o', **kwargs)
            else:
                plt.plot(atlf[i], coe[i], 'o', **kwargs)

            slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(
                atlf[i], coe[i])
            plt.plot(atlf[i], intercept + slope*np.asarray(atlf[i]),
                     color=colors[i], lw=1.5, label=
                     '{}\nC/E = {:.4f}*ATLF + {:.4f}\n$R^2$={:.4f}'.format(
                         options['labels'][i], slope, intercept, r_value**2))

        plt.xlabel('Above-thermal leakage fraction', fontsize=18)
        plt.ylabel(r'$k_{\text{eff}}$ C/E', fontsize=18)
        plt.gcf().set_size_inches(12,6)

    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)
    title = '\n'.join([options['title'], 'Author: ' + options['author'],
                       time.ctime()]).strip()
    plt.title(title, multialignment='left')
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
