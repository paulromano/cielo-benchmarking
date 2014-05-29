#!/usr/bin/env python

import sys
from math import sqrt
from collections import OrderedDict
import argparse

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import brewer2mpl
import xlrd

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('xlsfiles', nargs='+', help='Path to XLS file')
parser.add_argument('-s', '--save', action='store_true',
                    help='Save figure rather than showing it')
parser.add_argument('-r', '--region', action='store_true',
                    help='Show uncertainty of mean in shaded region')
parser.add_argument('-e', '--error', action='store_true',
                    help='Show error bars on individual points')
parser.add_argument('-t', '--title', action='store', help='Plot title')
args = parser.parse_args()

# Read data from files
labels = OrderedDict()
x = []
keff = []
stdev = []
count = 0
for xls in args.xlsfiles:
    book = xlrd.open_workbook(xls)
    sheet = book.sheet_by_index(0)

    x.append([])
    keff.append([])
    stdev.append([])
    for i in range(sheet.nrows - 1):
        words = sheet.cell(i, 0).value.split('/')
        benchmark = words[1] + '/' + words[3]
        if benchmark in labels:
            count =  labels[benchmark]
        else:
            count += 1
            labels[benchmark] = count

        x[-1].append(count)
        keff[-1].append(sheet.cell(i, 1).value)
        stdev[-1].append(1.96 * sheet.cell(i, 2).value)

# Get pretty color map
n = len(labels)
colors = brewer2mpl.get_map('Set2', 'qualitative', max(3,min(8,n))).mpl_colors

# Plot data
for i in range(len(x)):
    if args.error:
        plt.errorbar(x[i], keff[i], yerr=stdev[i], fmt='o', color=colors[i],
                     mec='black', mew=0.15)
    else:
        plt.plot(x[i], keff[i], 'o', color=colors[i], mec='black', mew=0.15)

    mu = sum(keff[i])/len(keff[i])
    sigma = sqrt(sum([s**2 for s in stdev[i]]))/len(stdev[i])

    if args.region:
        ax = plt.gca()
        verts = [(-1, mu - sigma), (-1, mu + sigma), (n, mu + sigma), (n, mu - sigma)]
        poly = Polygon(verts, facecolor=colors[i], alpha=0.5)
        ax.add_patch(poly)
    else:
        plt.plot([-1,n], [mu, mu], '-', color=colors[i], lw=1.5)

# Configure plot
ax = plt.gca()
plt.xticks(range(n), labels.keys(), rotation='vertical')
plt.xlim((-1,n))
plt.subplots_adjust(bottom=0.30)
plt.setp(ax.get_xticklabels(), fontsize=10)
plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
plt.gca().set_axisbelow(True)
plt.ylabel('k-effective', fontsize=16)
plt.gcf().set_size_inches(17,6)
if args.title:
    plt.title(args.title)
plt.show()
#plt.savefig('benchmarks.pdf', bbox_inches='tight')
