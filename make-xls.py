#!/usr/bin/env python

import sys

import xlwt

if len(sys.argv) < 2:
    sys.exit('Usage: make-xlsx.py results.txt')

book = xlwt.Workbook(encoding='utf-8')
sheet = book.add_sheet("Results")

with open(sys.argv[1], 'r') as f:
    for row, line in enumerate(f):
        words = line.split()
        benchmark = words[0]
        keff = float(words[1])
        stdev = float(words[2])

        sheet.write(row, 0, benchmark)
        sheet.write(row, 1, keff)
        sheet.write(row, 2, stdev)

sheet.write(row+1, 0, "AVERAGE")
cells = "B{0}:B{1}".format(1, row+1)
sheet.write(row+1, 1, xlwt.Formula("AVERAGE({0})".format(cells)))
sheet.write(row+1, 2, xlwt.Formula("STDEV({0})/SQRT(COUNT({0}))".format(cells)))

sheet.col(0).width = 256*40
book.save(sys.argv[1] + '.xls')
