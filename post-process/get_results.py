#!/usr/bin/env python

import argparse
from collections import defaultdict
import tarfile
import os
import re

try:
    from icsbep.icsbep import model_keff
except ImportError:
    model_keff = {}

numeric_pattern = r"[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)"

parser = argparse.ArgumentParser()
parser.add_argument('tarfile', action='store', help='tar file')
parser.add_argument('-s', '--summary', action='store_true', dest='summary', help='Show summary information')
parser.add_argument('-x', '--xls', action='store', dest='xls', help='Spreadsheet to write')
args = parser.parse_args()

data = {}

# ==============================================================================
# Get list of benchmarks from tar and accumulate basic information

f = tarfile.open(args.tarfile, 'r')
filenames = f.getnames()
for filename in filenames:
    # Get benchmark model and case
    path = os.path.relpath(os.path.dirname(filename), 'benchmarks')
    words = path.split('/')
    model = words[1]
    volume, form, spectrum, number = model.split('-')
    abbreviation = volume[0] + form[0] + spectrum[0]
    if len(words) >= 4:
        benchmark = model + '/' + words[3]
        case = words[3].replace('case', '')
    else:
        benchmark = model
        case = ''

    # Create dictionary for benchmark
    if benchmark not in data:
        data[benchmark] = {}

    # Store names of tallies and output files
    if 'tallies' in filename:
        data[benchmark]['tallies'] = filename
    else:
        data[benchmark]['output'] = filename

    # Get benchmark model k-effective and uncertainty
    if benchmark in model_keff:
        data[benchmark]['keff_model'] = model_keff[benchmark]
    else:
        if 'output' in filename:
            print('Warning: No benchmark value for {}'.format(benchmark))

# ==============================================================================
# Parse output files for results

for benchmark in data:
    output = f.extractfile(data[benchmark]['output'])
    for line in output:
        # k-effective
        m = re.search(r'Combined k-effective.*(\d+\.\d+).*(\d+\.\d+)', line)
        if m:
            data[benchmark]['keff'] = map(float, m.groups())

        # Leakage
        m = re.search(r'Leakage Fraction.*(\d+\.\d+).*(\d+\.\d+)', line)
        if m:
            data[benchmark]['leakage'] = map(float, m.groups())

        # ATLF
        m = re.search(r'Above-thermal Leakage.*(\d+\.\d+).*(\d+\.\d+)', line)
        if m:
            data[benchmark]['atlf'] = map(float, m.groups())

    tallies = f.extractfile(data[benchmark]['tallies'])
    tally_data = tallies.read()

    # O-16 absorption rate
    m = re.search(r'O-16.*?Absorption Rate\s+({0}).*?({0})'.format(numeric_pattern),
                  tally_data, re.MULTILINE | re.DOTALL)
    if m:
        data[benchmark]['O-16_abs'] = map(float, m.groups())

    # Pu-239 fission rate
    m = re.search(r'Pu-239.*?Fission Rate\s+({0}).*?({0})'.format(numeric_pattern),
                  tally_data, re.MULTILINE | re.DOTALL)
    if m:
        data[benchmark]['Pu-239_fis'] = map(float, m.groups())

# ==============================================================================
# Show average C/E if requested

if args.summary:
    from tabulate import tabulate

    avg = defaultdict(float)
    count = defaultdict(int)
    for benchmark in data:
        d = data[benchmark]

        value = (d['keff'][0] / d['keff_model'][0] - 1)*1e5

        words = benchmark.split('/')
        model = words[0].split('-')
        category = model[0][0] + model[2][0]
        if category not in avg:
            avg[category] = 0.0
            count[category] = 0
        avg[category] += value
        count[category] += 1

    for category in avg:
        avg[category] /= count[category]

    headers = ["Fuel", "therm", "inter", "fast", "mixed"]
    table = [['HEU', count['ht'], count['hi'], count['hf'], count['hm']],
             ['LEU', count['lt'], count['li'], count['lf'], count['lm']],
             ['IEU', count['it'], count['ii'], count['if'], count['im']],
             ['Pu', count['pt'], count['pi'], count['pf'], count['pm']],
             ['U233', count['ut'], count['ui'], count['uf'], count['um']],
             ['Mix', count['mt'], count['mi'], count['mf'], count['mm']]]
    print("BENCHMARK COUNT")
    print(tabulate(table, headers=headers, tablefmt="grid"))

    headers = ["Fuel", "therm", "inter", "fast", "mixed"]
    table = [['HEU', avg['ht'], avg['hi'], avg['hf'], avg['hm']],
             ['LEU', avg['lt'], avg['li'], avg['lf'], avg['lm']],
             ['IEU', avg['it'], avg['ii'], avg['if'], avg['im']],
             ['Pu', avg['pt'], avg['pi'], avg['pf'], avg['pm']],
             ['U233', avg['ut'], avg['ui'], avg['uf'], avg['um']],
             ['Mix', avg['mt'], avg['mi'], avg['mf'], avg['mm']]]
    print("\nAVERAGE C/E DEVIATION")
    print(tabulate(table, headers=headers, tablefmt="grid"))



# ==============================================================================
# Create spreadsheet if requested

if args.xls:
    import xlwt

    book = xlwt.Workbook(encoding='utf-8')
    sheet = book.add_sheet("Results")

    columns = {}
    all_models = sorted(data.keys())
    col = 1

    sheet.write(0, 0, 'benchmark')

    for row, benchmark in enumerate(all_models):
        d = data[benchmark]
        sheet.write(row + 1, 0, benchmark)
        for key in d:
            if key in ('tallies', 'output'):
                continue
            if key not in columns:
                sheet.write(0, col, key)
                columns[key] = col
                col += 2

            sheet.write(row + 1, columns[key], d[key][0])
            sheet.write(row + 1, columns[key] + 1, d[key][1])

    sheet.col(0).width = 256*40
    book.save(args.xls)
