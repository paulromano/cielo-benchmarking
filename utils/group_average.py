#!/usr/bin/env python

from __future__ import division
from math import sqrt
from random import sample

import numpy as np
from tabulate import tabulate
from uncertainties import ufloat
import xlrd

sheet = xlrd.open_workbook("NRG_VanDerMark_Tables.xlsx").sheet_by_index(0)

k_values = {'all': []}
for i in range(sheet.nrows):
    cross_section = sheet.cell(i, 4).value
    if cross_section != "ENDF/B-VII.1":
        continue

    model = sheet.cell(i, 0).value
    k_mean = float(sheet.cell(i, 5).value)

    series = model[:3]
    if series not in k_values:
        k_values[series] = []
    k_values[series].append(k_mean)
    k_values['all'].append(k_mean)

results = []
for series in sorted(k_values):
    for n_group in [30, 60, 100, 300]:
        if len(k_values[series]) <= n_group:
            continue
        for n_samples in [10000]:
            print('{}, {}, {}'.format(series, n_group, n_samples))
            averages = np.zeros(n_samples)
            for i in range(n_samples):
                values = sample(k_values[series], n_group)
                averages[i] = sum(values)/n_group

            overall_avg = ufloat(np.mean(averages), np.std(averages))
            results.append([series, len(k_values[series]), n_group, n_samples, '{:.5f}'.format(overall_avg),
                            '{:.5f}'.format(min(averages)), '{:.5f}'.format(max(averages))])

header = ['Series', 'Benchmarks', 'Group size', 'Samples', 'Average', 'Min', 'Max']
print(tabulate(results, headers=header, tablefmt='rst'))
