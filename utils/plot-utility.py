#!/usr/bin/env python3

import sys
from math import sqrt
import os
from fnmatch import fnmatch
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import Tk

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd


sys.path.insert(0, '/home/romano/benchmarks/icsbep')
from icsbep.icsbep import model_keff


def benchmark_name(excel_label):
    if '/' not in excel_label: return excel_label
    words = excel_label.split('/')
    model = words[1]
    volume, form, spectrum, number = model.split('-')
    if len(words) >= 4:
        return model + '/' + words[3]
    else:
        return model


def short_name(name):
    model, *case = name.split('/')
    volume, form, spectrum, number = model.split('-')
    abbreviation = volume[0] + form[0] + spectrum[0]
    if case:
        casenum = case[0].replace('case', '')
    else:
        casenum = ''
    return f'{abbreviation}{int(number)}{casenum}'


def get_result_dataframe(filename):
    df = pd.read_excel(
        filename,
        header=None,
        names=['name', 'keff', 'stdev'],
        usecols='A:C',
        converters={'name': benchmark_name}
    )
    df.set_index("name", inplace=True)

    # Get rid of last row
    df.drop("AVERAGE", inplace=True)
    return df


def get_icsbep_dataframe():
    keff = [x[0] for x in model_keff.values()]
    stdev = [x[1] for x in model_keff.values()]
    data = {'keff': keff, 'stdev': stdev}
    return pd.DataFrame(data, index=model_keff.keys())


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
    return int(input('--> '))

def add_file():
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=(("Spreadsheets", "*.xls*"),
                                          ("All", "*.*")))
    root.destroy()
    label = input('Enter label: ') if filename else None
    return label, filename

def set_options(options):
    choice = None
    while choice != 9:
        os.system('clear')
        print("""
1) Plot type                                     [{plot_type}]
2) Show shaded uncertainties around mean         [{show_shaded}]
3) Show error bars on individual cases           [{show_uncertainties}]
4) Show legend                                   [{show_legend}]
5) Case name pattern match                       [{match}]
6) Title                                         [{title}]
7) X-axis label                                  [{xlabel}]
8) Y-axis label                                  [{ylabel}]
9) Return to main menu
""".format(**options))
        choice = int(input('--> '))
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
            options['xlabel'] = input('Enter x-label: ')
        elif choice == 8:
            options['ylabel'] = input('Enter y-label: ')

def set_file_main(options):
    n = len(options['files'])
    choice = None
    while choice != n + 1:
        os.system('clear')
        print("Select file:")
        for i, filename in enumerate(options['files']):
            print(f"{i + 1}) {filename}")
        print(f"{n + 1}) Return to main menu")
        choice = int(input('--> '))
        if choice != n + 1:
            set_file_options(options, choice - 1)

def set_file_options(options, i):
    choice = None
    while choice != 2:
        os.system('clear')
        print("""
1) File label                                    [{}]
2) Return to file selection
""".format(options['labels'][i]))
        choice = int(input('--> '))
        if choice == 1:
            options['labels'][i] = input('Enter label: ')

def plot(options, save=False):
    # Read data from spreadsheets
    dataframes = {}
    for xls, label in zip(options['files'], options['labels']):
        dataframes[label] = get_result_dataframe(xls)

    # Get model keff and uncertainty from ICSBEP
    icsbep = get_icsbep_dataframe()

    # Determine common benchmarks
    base = options['labels'][0]
    index = dataframes[base].index
    for df in dataframes.values():
        index = index.intersection(df.index)

    # Applying matching as needed
    if options['match']:
        cond = index.map(lambda x: fnmatch(x, options['match']))
        index = index[cond]

    # Setup x values (integers) and corresponding tick labels
    n = index.size
    x = range(1, n + 1)
    xticklabels = index.map(short_name)

    # Plot data
    if options['plot_type'] == 'keff':
        for i, (label, df) in enumerate(dataframes.items()):
            coe = (df['keff'] / icsbep['keff']).loc[index]
            stdev = 1.96 * df['stdev'].loc[index]

            kwargs = {'color': f'C{i}', 'mec': 'black', 'mew': 0.15}
            if options['show_legend']:
                kwargs['label'] = label

            if options['show_uncertainties']:
                plt.errorbar(x, coe, yerr=stdev, fmt='o', **kwargs)
            else:
                plt.plot(x, coe, 'o', **kwargs)

            mu = coe.mean()
            sigma = coe.std() / sqrt(n)
            if options['show_shaded']:
                ax = plt.gca()
                verts = [(0, mu - sigma), (0, mu + sigma), (n+1, mu + sigma), (n+1, mu - sigma)]
                poly = Polygon(verts, facecolor=f'C{i}', alpha=0.5)
                ax.add_patch(poly)
            else:
                plt.plot([-1,n], [mu, mu], '-', color=f'C{i}', lw=1.5)

        # Show shaded region of benchmark model uncertainties
        uncverts = []
        for i, benchmark in enumerate(index):
            unc = 0.0 if benchmark not in model_keff else model_keff[benchmark][1]
            uncverts.append((1 + i, 1 + unc))
        for i, benchmark in enumerate(index[::-1]):
            unc = 0.0 if benchmark not in model_keff else model_keff[benchmark][1]
            uncverts.append((n - i, 1 - unc))
        poly = Polygon(uncverts, facecolor='gray', edgecolor=None, alpha=0.2)
        ax = plt.gca()
        ax.add_patch(poly)

    elif options['plot_type'] == 'diff':
        kwargs = {'mec': 'black', 'mew': 0.15, 'fmt': 'o'}

        keff0 = dataframes[base]['keff'].loc[index]
        stdev0 = dataframes[base]['stdev'].loc[index]
        for i, label in enumerate(options['labels'][1:]):
            df = dataframes[label]
            keff_i = df['keff'].loc[index]
            stdev_i = df['stdev'].loc[index]

            diff = keff_i - keff0
            err = np.sqrt(stdev_i**2 + stdev0**2)
            kwargs['label'] = options['labels'][i + 1] + ' - ' + options['labels'][0]
            if options['show_uncertainties']:
                plt.errorbar(x, diff, yerr=err, color=f'C{i}', **kwargs)
            else:
                plt.plot(x, diff, color=f'C{i}', **kwargs)

            mu = diff.mean()
            if options['show_shaded']:
                sigma = diff.std() / sqrt(n)
                ax = plt.gca()
                verts = [(0, mu - sigma), (0, mu + sigma), (n+1, mu + sigma), (n+1, mu - sigma)]
                poly = Polygon(verts, facecolor=f'C{i}', alpha=0.5)
                ax.add_patch(poly)
            else:
                plt.plot([-1,n], [mu, mu], '-', color=f'C{i}', lw=1.5)

    # Configure plot
    ax = plt.gca()
    plt.xticks(x, xticklabels, rotation='vertical')
    plt.xlim((0,n+1))
    plt.subplots_adjust(bottom=0.15)
    plt.setp(ax.get_xticklabels(), fontsize=10)
    plt.setp(ax.get_yticklabels(), fontsize=14)
    plt.gcf().set_size_inches(17, 6)
    plt.xlabel(options['xlabel'], fontsize=18)
    plt.ylabel(options['ylabel'], fontsize=18)
    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)
    if options['title']:
        plt.title(options['title'], multialignment='left')
    if options['show_legend']:
        lgd = plt.legend(numpoints=1)

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
    options = {
        'files': [],
        'labels': [],
        'plot_type': 'keff',
        'show_shaded': True,
        'show_uncertainties': True,
        'show_legend': True,
        'xlabel': 'Benchmark case',
        'ylabel': r'$k_{\mathrm{eff}}$ C/E',
        'match': '',
        'title': '',
    }

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
