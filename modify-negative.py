#!/usr/bin/env python

from __future__ import print_function
import copy

import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate
from fudge.legacy.converting.endfFileToGND import endfFileToGND

# This is the "change" parameter by which all data is adjusted
target = 0.05

# Create ReactionSuite from ENDF file
print('Converting ENDF to GND...')
eval, cov = endfFileToGND('n-094_Pu_239.endf', toStdOut=False, toStdErr=False)

# Reconstruct resonances
print('Reconstructing resonances...')
eval.reconstructResonances()

# Get reactions
originalCapture2200 = eval.getReaction('capture').getCrossSection()['linear'].getValue(0.0253)
originalFission2200 = eval.getReaction('fission').getCrossSection()['linear'].getValue(0.0253)
print('Original 2200 m/s capture xs = {0}'.format(originalCapture2200))
print('Original 2200 m/s fission xs = {0}'.format(originalFission2200))

# Get RM parameters -- this returns a Fudge math.table object
params = eval.resonances.resolved.regions[0].nativeData.resonanceParameters
originalData = copy.deepcopy(params.data)

# Get energy column and column indices for partial-widths
energy = params.getColumn('energy')
columnNames = [col.name for col in params.columns]
colN = columnNames.index('neutronWidth')
colG = columnNames.index('captureWidth')
colFA = columnNames.index('fissionWidthA')
colFB = columnNames.index('fissionWidthB')

xg = 0.1
xf = 0.1
iteration = 1
while True:
    print('Iteration ' + str(iteration))
    print('  Changing capture widths by {0} percent'.format(xg*100))
    print('  Changing fission widths by {0} percent'.format(xf*100))

    # Save original values
    GG = [params.data[i][colG] for i in range(4)]
    GFA = [params.data[i][colFA] for i in range(4)]
    GFB = [params.data[i][colFB] for i in range(4)]

    # Increase capture widths and decrease fission widths for negative energy
    # resonances -- note that if the width is negative, we do the opposite
    for row in range(4):
        if params.data[row][colG] > 0:
            params.data[row][colG] *= 1 + xg
        else:
            params.data[row][colG] *= 1 - xg
        if params.data[row][colFA] > 0:
            params.data[row][colFA] *= 1 - xf
        else:
            params.data[row][colFA] *= 1 + xf
        if params.data[row][colFB] > 0:
            params.data[row][colFB] *= 1 - xf
        else:
            params.data[row][colFB] *= 1 + xf

    # Reconstruct resonances
    print('  Reconstructing resonances...')
    eval.reconstructResonances()

    # Get 2200 m/s values
    capture2200 = eval.getReaction('capture').getCrossSection()['linear'].getValue(0.0253)
    fission2200 = eval.getReaction('fission').getCrossSection()['linear'].getValue(0.0253)

    changeCapture = (capture2200 - originalCapture2200) / originalCapture2200
    changeFission = (fission2200 - originalFission2200) / originalFission2200

    print('  2200 m/s capture xs = {0} ({1})'.format(capture2200, changeCapture))
    print('  2200 m/s fission xs = {0} ({1})'.format(fission2200, changeFission))

    iteration += 1
    if (abs(target/changeCapture - 1) < 0.01 and
        abs(target/changeFission - 1) < 0.01):
        break

    # Reset partial widths
    for row in range(4):
        params.data[row][colG] = GG[row]
        params.data[row][colFA] = GFA[row]
        params.data[row][colFB] = GFB[row]

    xg *= target/changeCapture
    xf *= target/changeFission

# Print tables
headers = [col.name + (' ({0})'.format(col.units) if col.units else '')
          for col in params.columns]
print('\nORIGINAL RESONANCE PARAMETERS')
print(tabulate(originalData[:4], headers=headers, tablefmt='grid'))
print('\nMODIFIED RESONANCE PARAMETERS')
print(tabulate(params.data[:4], headers=headers, tablefmt='grid'))

# Write out modified ENDF file
#myENDF = eval.toENDF6({'verbosity': 0}, covarianceSuite=cov)
#open('junk.endf', 'w').write(myENDF)
