#!/usr/bin/env python

import sys
from math import sqrt
from collections import OrderedDict
import argparse

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
"""]
matplotlib.rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})


# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('xlsfiles', nargs='+', help='Path to XLS file')
parser.add_argument('-f', '--file', action='store',
                    help='Filename to save figure to')
parser.add_argument('-s', '--shade', action='store_true',
                    help='Show uncertainty of mean in shaded region')
parser.add_argument('-e', '--error', action='store_true',
                    help='Show error bars on individual points')
parser.add_argument('-t', '--title', action='store', help='Plot title')
args = parser.parse_args()

# Read data from files
labels = OrderedDict()
x = []
coe = []
stdev = []
count = 0
benchmark_list = []
for xls in args.xlsfiles:
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
    if args.error:
        plt.errorbar(x[i], coe[i], yerr=stdev[i], fmt='o', color=colors[i],
                     mec='black', mew=0.15)
    else:
        plt.plot(x[i], coe[i], 'o', color=colors[i], mec='black', mew=0.15)

    mu = sum(coe[i])/len(coe[i])
    sigma = sqrt(sum([s**2 for s in stdev[i]]))/len(stdev[i])

    if args.shade:
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
plt.gca().set_axisbelow(True)
plt.ylabel(r'$k_{\text{eff}}$ C/E', fontsize=18)
plt.gcf().set_size_inches(17,6)
if args.title:
    plt.title(args.title)

if args.file:
    plt.savefig(args.file, bbox_inches='tight')
else:
    plt.show()
