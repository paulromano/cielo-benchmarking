#!/usr/bin/env python

import sys
from math import sqrt
from collections import OrderedDict
import argparse
import os
from fnmatch import fnmatch
from tkFileDialog import askopenfilename, asksaveasfilename
from Tkinter import Tk

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import brewer2mpl
import xlrd

from benchmarks import results

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
2) Set options
3) Plot (save file)
4) Plot (show)
5) Exit

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
    return filename

def set_options(options):
    os.system('clear')
    print("""
1) Show shaded uncertainties around mean         [{show_shaded}]
2) Show error bars on individual cases           [{show_uncertainties}]
3) Case name pattern match                       [{match}]
4) Plot title                                    [{title}]
5) Return to main menu
""".format(**options))
    choice = eval(raw_input('--> '))
    if choice == 1:
        options['show_shaded'] = not options['show_shaded']
    elif choice == 2:
        options['show_uncertainties'] = not options['show_uncertainties']
    elif choice == 3:
        options['match'] = raw_input('Enter matching pattern: ')
    elif choice == 4:
        options['title'] = raw_input('Enter title: ')
    elif choice == 5:
        return
    set_options(options)

def plot(files, options, save=False):
    # Read data from files
    labels = OrderedDict()
    x = []
    coe = []
    stdev = []
    count = 0
    benchmark_list = []
    for xls in files:
        book = xlrd.open_workbook(xls)
        sheet = book.sheet_by_index(0)

        x.append([])
        coe.append([])
        stdev.append([])
        for i in range(sheet.nrows - 1):
            words = sheet.cell(i, 0).value.split('/')
            if len(words) >= 4:
                benchmark = words[1] + '/' + words[3]
            else:
                benchmark = words[1] + '/case-1'
            if options['match']:
                if not fnmatch(benchmark, options['match']):
                    continue
            model, case = benchmark.split('/')
            volume, form, spectrum, number = model.split('-')
            abbreviation = volume[0] + form[0] + spectrum[0]
            name = '{}{}{}'.format(abbreviation, int(number),
                                   case.replace('case', ''))

            if name in labels:
                count = labels[name]
            else:
                count += 1
                labels[name] = count
                benchmark_list.append(benchmark)

            x[-1].append(count)
            coe[-1].append(sheet.cell(i, 1).value/results[benchmark][0])
            stdev[-1].append(1.96 * sheet.cell(i, 2).value)

    # Get pretty color map
    n = len(labels)
    colors = brewer2mpl.get_map('Set2', 'qualitative', max(3,min(8,n))).mpl_colors

    # Plot data
    for i in range(len(x)):
        if options['show_uncertainties']:
            plt.errorbar(x[i], coe[i], yerr=stdev[i], fmt='o', color=colors[i],
                         mec='black', mew=0.15)
        else:
            plt.plot(x[i], coe[i], 'o', color=colors[i], mec='black', mew=0.15)

        mu = sum(coe[i])/len(coe[i])
        sigma = sqrt(sum([s**2 for s in stdev[i]]))/len(stdev[i])

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
        uncverts.append((1 + i, 1 + results[benchmark][1]))
    for i, benchmark in enumerate(benchmark_list[::-1]):
        uncverts.append((n - i, 1 - results[benchmark][1]))
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
    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    ax.set_axisbelow(True)
    plt.ylabel(r'$k_{\text{eff}}$ C/E', fontsize=18)
    plt.gcf().set_size_inches(17,6)
    if options['title']:
        plt.title(options['title'])

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
    files = []
    options = {'show_shaded': True,
               'show_uncertainties': False,
               'match': '',
               'title': ''}

    while True:
        choice = get_input(files)
        if choice == 1:
            filename = add_file()
            if filename:
                files.append(filename)

        elif choice == 2:
            set_options(options)
        elif choice == 3:
            plot(files, options, True)
        elif choice == 4:
            plot(files, options)
        elif choice == 5:
            break

