#!/usr/bin/env python

from __future__ import print_function
import copy

import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate
from fudge.legacy.converting.endfFileToGND import endfFileToGND

# File to convert
endffile = 'endf-b-vii-1.endf'

# Relative uncertainties:
#
#    Energy range   total   capture   fission   elastic
#    --------------------------------------------------
#       E < 0.1      1.4%      4.2%      0.9%      4.6%
#     0.1 - 0.54     1.9%      4.2%      1.9%      3.7%
#    0.54 - 4        1.3%      3.6%      1.1%      4.3%
#       4 - 22.6     3.1%      7.1%      3.0%      3.3%
#    22.6 - 454      3.9%      6.5%      3.5%      5.7%
#     454 - 2500     3.2%      5.1%      3.2%      4.0%

uCapture = 0.042
uFission = 0.009

# This is the "change" parameter by which all data is adjusted
target = 0.5
targetCapture = target*uCapture
targetFission = -target*uFission
initial_guess = 0.1

# Create ReactionSuite from ENDF file
print('Targeting a {0}% increase in 2200 m/s capture'.format(targetCapture*100).upper())
print('Targeting a {0}% decrease in 2200 m/s fission\n'.format(targetFission*100).upper())
print('Reading data from {0}...'.format(endffile))
translation = endfFileToGND(endffile, toStdOut=False, toStdErr=False)
eval = translation['reactionSuite']

# Reconstruct resonances
print('Reconstructing resonances...')
eval.reconstructResonances()

# Get reactions
capture = eval.getReaction('capture').getCrossSection()['linear']
fission = eval.getReaction('fission').getCrossSection()['linear']
originalCapture2200 = capture.getValue(0.0253)
originalFission2200 = fission.getValue(0.0253)
originalCaptureXS = zip(*capture[:])
originalFissionXS = zip(*fission[:])
print('Original 2200 m/s capture xs = {0:.3f} b'.format(originalCapture2200))
print('Original 2200 m/s fission xs = {0:.3f} b'.format(originalFission2200))

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

xg = initial_guess*uCapture
xf = initial_guess*uFission
iteration = 1
while True:
    print('Iteration ' + str(iteration))
    print('  Changing capture widths by {0:.1f}%'.format(xg*100))
    print('  Changing fission widths by {0:.1f}%'.format(xf*100))

    # Save original values
    GG = [params.data[i][colG] for i in range(4)]
    GFA = [params.data[i][colFA] for i in range(4)]
    GFB = [params.data[i][colFB] for i in range(4)]

    # Increase capture widths and decrease fission widths for negative energy
    # resonances -- note that if the width is negative, we do the opposite
    for row in range(4):
        params.data[row][colG] *= 1 + xg
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
    capture = eval.getReaction('capture').getCrossSection()['linear']
    fission = eval.getReaction('fission').getCrossSection()['linear']
    capture2200 = capture.getValue(0.0253)
    fission2200 = fission.getValue(0.0253)
    captureXS = zip(*capture[:])
    fissionXS = zip(*fission[:])

    changeCapture = (capture2200 - originalCapture2200) / originalCapture2200
    changeFission = (fission2200 - originalFission2200) / originalFission2200

    print('  2200 m/s capture xs = {0:.3f} b ({1:.2f}%)'.format(capture2200, changeCapture*100))
    print('  2200 m/s fission xs = {0:.3f} b ({1:.2f}%)'.format(fission2200, changeFission*100))

    iteration += 1
    if (abs(targetCapture/changeCapture - 1) < abs(targetCapture)*0.1 and
        abs(targetFission/changeFission - 1) < abs(targetFission)*0.1):
        break

    # Reset partial widths
    for row in range(4):
        params.data[row][colG] = GG[row]
        params.data[row][colFA] = GFA[row]
        params.data[row][colFB] = GFB[row]

    xg *= targetCapture/changeCapture
    xf *= targetFission/changeFission

# Print tables
headers = [col.name + (' ({0})'.format(col.units) if col.units else '')
          for col in params.columns]
print('\nORIGINAL RESONANCE PARAMETERS')
print(tabulate(originalData[:4], headers=headers, tablefmt='grid'))
print('\nMODIFIED RESONANCE PARAMETERS')
print(tabulate(params.data[:4], headers=headers, tablefmt='grid'))

# Display plot of original/modified
plt.loglog(originalCaptureXS[0], originalCaptureXS[1])
plt.loglog(captureXS[0], captureXS[1])
plt.grid(True)
plt.xlabel('Energy (eV)')
plt.ylabel('Cross section (b)')
plt.show()

# Write out modified ENDF file
#myENDF = eval.toENDF6({'verbosity': 0}, covarianceSuite=cov)
#open('junk.endf', 'w').write(myENDF)
