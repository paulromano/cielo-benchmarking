#!/usr/bin/env python

"""
Plot types:

Y data type
X data:

q1 vs benchmark
q1 vs q2
q1/q2 vs benchmark
q1 - q2 vs benchmark
(q1 - q2)/q1 vs benchmark

Quantity (1)
Ratio (2)
Difference (1)
Relative difference (1)
"""

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
import IPython

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

def short_name(name):
    words = name.split('/')
    model = words[0]
    volume, form, spectrum, number = model.split('-')
    abbreviation = volume[0] + form[0] + spectrum[0] + str(int(number))
    if len(words) >= 2:
        abbreviation += words[1].replace('case', '')
    return abbreviation

class PlotUtility(object):
    def __init__(self):
        # Initialize data and set defaults
        self.data = []
        self.xdata = 'benchmark'
        self.xlabel = 'Benchmark case'
        self.ydata = 'ratio keff keff_model'
        self.ylabel = r'$k_{\text{eff}}$ C/E'
        self.show_shaded = True
        self.show_uncertainties = False
        self.show_legend = True
        self.match = ''
        self.exclude = None
        self.title = ''
        self.author = 'Paul Romano'

        while True:
            self.show_options(['Add file', 'Set plot options', 'Set file options',
                               'Plot (save file)', 'Plot (show)', 'Exit'])
            print("Files:")
            for d in self.data:
                print('  ' + d['filename'])
            print('')
            choice = int(raw_input('--> '))
            if choice == 1:
                self.load_file()
            elif choice == 2:
                self.set_options()
            elif choice == 3:
                self.set_file_main()
            elif choice == 4:
                self.plot(True)
            elif choice == 5:
                self.plot()
            elif choice == 6:
                break

    def show_options(self, items):
        os.system("clear")
        maxlen = max([len(i[0]) if isinstance(i, tuple) else len(i)
                      for i in items])
        for i, item in enumerate(items):
            if isinstance(item, tuple):
                print("{:2}) {}{} [{}]".format(i + 1, item[0], ' '*(maxlen - len(item[0])),
                                         item[1]))
            else:
                print("{:2}) {}".format(i + 1, item))

    def load_file(self):
        root = Tk()
        root.withdraw()
        filename = askopenfilename(filetypes=(("Spreadsheets", "*.xls*"),
                                          ("All", "*.*")))
        root.destroy()
        label = raw_input('Enter label: ')

        book = xlrd.open_workbook(filename)
        sheet = book.sheet_by_index(0)

        quantities = sheet.row_values(0)[1::2]
        results = {quantity: {} for quantity in quantities}
        for i in range(1, sheet.nrows):
            words = sheet.cell(i, 0).value.split('/')
            model = words[0]
            volume, form, spectrum, number = model.split('-')
            if len(words) >= 2:
                benchmark = model + '/' + words[1]
            else:
                benchmark = model

            j = 1
            for quantity in quantities:
                value = sheet.cell_value(i, j)
                uncert = sheet.cell_value(i, j + 1)
                results[quantity][benchmark] = (value, uncert)
                j += 2

        self.data.append({'label': label, 'filename': filename, 'results': results})
        return

    def set_options(self):
        choice = None
        while choice != 'Return to main menu':
            choices = [('X-axis data', self.xdata), ('X-axis label', self.xlabel),
                       ('Y-axis data', self.ydata), ('Y-axis label', self.ylabel),
                       ('Show uncertainties around mean', self.show_shaded),
                       ('Show error bars on individual cases', self.show_uncertainties),
                       ('Show legend', self.show_legend),
                       ('Case name pattern match', self.match), ('Title', self.title),
                       ('Author', self.author), 'Return to main menu']
            self.show_options(choices)
            choice = choices[int(raw_input('--> ')) - 1]
            if isinstance(choice, tuple): choice = choice[0]

            if choice in ('X-axis data', 'Y-axis data'):
                quantities = set()
                for data in self.data:
                    quantities.update(data['results'].keys())
                print('Available quantities:')
                for q in quantities:
                    print('  ' + q)

            if choice == 'X-axis data':
                self.xdata = raw_input('Enter x-axis data: ')
            elif choice == 'X-axis label':
                self.xlabel = raw_input('Enter x-label: ')
            elif choice == 'Y-axis data':
                self.ydata = raw_input('Enter y-axis data: ')
            elif choice == 'Y-axis label':
                self.ylabel = raw_input('Enter y-label: ')
            elif choice == 'Show uncertainties around mean':
                self.show_shaded = not self.show_shaded
            elif choice == 'Show error bars on individual cases':
                self.show_uncertainties = not self.show_uncertainties
            elif choice == 'Show legend':
                self.show_legend = not self.show_legend
            elif choice == 'Case name pattern match':
                self.match = raw_input('Enter matching pattern: ')
            elif choice == 'Title':
                self.title = raw_input('Enter title: ')
            elif choice == 'Author':
                self.author = raw_input('Enter author: ')

    def set_file_main(self):
        n = len(self.data)
        choice = None
        while choice != n + 1:
            self.show_options([d['filename'] for d in self.data] + ['Return to main menu'])
            choice = int(raw_input('--> '))
            if choice != n + 1:
                self.set_file_options(choice - 1)
            n = len(self.data)

    def set_file_options(self, i):
        choice = None
        while choice != 3:
            choices = [('File label', self.data[i]['label']), 'Remove file',
                       'Return to file selection']
            self.show_options(choices)
            choice = int(raw_input('--> '))
            if choice == 1:
                self.data[i]['label'] = raw_input('Enter label: ')
            elif choice == 2:
                self.data.pop(i)
                return

    def plot(self, save=False):
        count = 0
        coe = False
        xindex = OrderedDict()
        n = len(self.data)
        colors = brewer2mpl.get_map('Set2', 'qualitative', max(3,min(8,n))).mpl_colors

        for i, d in enumerate(self.data):
            if self.ydata.startswith('ratio'):
                words = self.ydata.split()
                q1 = words[1]
                q2 = words[2]
                results = d['results'][q1]
                results2 = d['results'][q2]
                if words == ['ratio', 'keff', 'keff_model'] and self.xdata == 'benchmark':
                    coe = True
            else:
                results = d['results'][self.ydata]

            x = []
            y = []
            yerr = []
            for benchmark, (value, uncert) in results.items():

                # Check for matching pattern
                if self.match:
                    if not fnmatch(benchmark, self.match):
                        continue

                if self.ydata.startswith('ratio'):
                    if benchmark not in results2:
                        continue
                    value /= results2[benchmark][0]

                if self.xdata == 'benchmark':
                    if benchmark not in xindex:
                        count += 1
                        xindex[benchmark] = count
                    x.append(xindex[benchmark])
                else:
                    if benchmark not in d['results'][self.xdata]:
                        continue
                    x.append(d['results'][self.xdata][benchmark][0])

                y.append(value)
                yerr.append(uncert)

            kwargs = {'color': colors[i], 'mec': 'black', 'mew': 0.15}
            if self.show_legend:
                kwargs['label'] = d['label']

            x = np.array(x)
            y = np.array(y)
            if self.show_uncertainties:
                plt.errorbar(x, y, yerr=yerr, fmt='o', **kwargs)
            else:
                plt.plot(x, y, 'o', **kwargs)

            if self.xdata != 'benchmark':
                slope, intercept, r_value, p_value, \
                    std_err = scipy.stats.linregress(x, y)
                plt.plot(x, intercept + slope*x, color=colors[i], lw=1.5)

        # Show benchmark model uncertainties for keff C/E plots
        if coe:
            uncverts = []
            for i, benchmark in enumerate(xindex.keys()):
                unc = 0.0 if benchmark not in model_keff else model_keff[benchmark][1]
                uncverts.append((1 + i, 1 + unc))
            for i, benchmark in enumerate(xindex.keys()[::-1]):
                unc = 0.0 if benchmark not in model_keff else model_keff[benchmark][1]
                uncverts.append((count - i, 1 - unc))
            poly = Polygon(uncverts, facecolor='gray', edgecolor=None, alpha=0.2)
            ax = plt.gca()
            ax.add_patch(poly)

        # For benchmark x-data, put proper labels on x axis
        if self.xdata == 'benchmark':
            plt.xticks(range(1,count+1), [short_name(i) for i in xindex.keys()],
                       rotation='vertical')
            plt.xlim((0,count+1))

        # Configure plot
        ax = plt.gca()
        plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
        plt.gca().set_axisbelow(True)
        plt.subplots_adjust(bottom=0.15)
        plt.setp(ax.get_xticklabels(), fontsize=10)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        plt.gcf().set_size_inches(17,6)
        plt.xlabel(self.xlabel, fontsize=18)
        plt.ylabel(self.ylabel, fontsize=18)
        title = '\n'.join([self.title, 'Author: ' + self.author,
                           time.ctime()]).strip()
        plt.title(title, multialignment='left')
        if self.show_legend:
            lgd = plt.legend(loc='center left', bbox_to_anchor=(1.0,0.5), numpoints=1)

        # Save or show plot
        if save:
            root = Tk()
            root.withdraw()
            filename = asksaveasfilename()
            root.destroy()
            if self.show_legend:
                plt.savefig(filename, bbox_extra_artists=(lgd,), bbox_inches='tight')
            else:
                plt.savefig(filename, bbox_inches='tight')
        else:
            plt.show()
        plt.close()


if __name__ == "__main__":
    util = PlotUtility()
