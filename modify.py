#!/usr/bin/env python

from __future__ import print_function
import copy
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from tabulate import tabulate
from fudge.legacy.converting.endfFileToGND import endfFileToGND

# File to convert
endffile = 'endf-b-vii-1.endf'

# This is the "change" parameter by which all data is adjusted
x = 0.25

def header(s):
    n = (77 - len(s))//2
    print('{0}\n{1} {2} {1}\n{0}\n'.format(
            '='*79, ' '*n, s, ' '*(79 - n+len(s)+2)))

# ==============================================================================
header('(1) Reading data from {0}'.format(endffile))
# ==============================================================================

translation = endfFileToGND(endffile, toStdOut=False, toStdErr=False)
eval = translation['reactionSuite']
cov = translation['covarianceSuite']

print('Reconstructing resonances...')
eval.reconstructResonances()

# Get capture and fission cross sections
capture = eval.getReaction('capture').getCrossSection()['linear']
fission = eval.getReaction('fission').getCrossSection()['linear']
originalCapture2200 = capture.getValue(0.0253)
originalFission2200 = fission.getValue(0.0253)
originalCaptureXS = np.asarray(capture.copyDataToXsAndYs())
originalFissionXS = np.asarray(fission.copyDataToXsAndYs())
print('Original 2200 m/s capture xs = {0:.3f} b'.format(originalCapture2200))
print('Original 2200 m/s fission xs = {0:.3f} b'.format(originalFission2200))

# Get RM parameters, column indices for partial-widths
params = eval.resonances.resolved.regions[0].nativeData.resonanceParameters

columnNames = [col.name for col in params.columns]
colN = columnNames.index('neutronWidth')
colG = columnNames.index('captureWidth')
colFA = columnNames.index('fissionWidthA')
colFB = columnNames.index('fissionWidthB')
headers = [col.name + (' ({0})'.format(col.units) if col.units else '')
          for col in params.columns]

originalData = copy.deepcopy(params.data)
print('ORIGINAL RESONANCE PARAMETERS')
print(tabulate(originalData[:6], headers=headers, tablefmt='grid') + '\n')

# ==============================================================================
header('(2) Modifying resonance parameters...')
# ==============================================================================

# Uncertainties in resonance parameters given by Gilles Noguerre. These are
# supposedly from SG34 file 32.

uCapture = 1.3e-3
uFission = 0.95e-3
row = 4
print('Uncertainty in 0.296 eV capture width = {0} eV'.format(uCapture))
print('Uncertainty in 0.296 eV fissionA width = {0} eV'.format(uFission))

# Increase radiation width for 0.3 eV resonance and decrease fission widths for
# 0.3 eV resonance -- note that for both this resonance and the 7.8 eV
# resonance, the second-chance fission partial-width is zero already so it
# doesn't need to be adjusted
params.data[row][colG] += x*uCapture
params.data[row][colFA] -= x*uFission

uCapture = 2.1e-3
uFission = 1.85e-3
row = 5
print('Uncertainty in 7.8 eV capture width = {0} eV'.format(uCapture))
print('Uncertainty in 7.8 eV fissionA width = {0} eV\n'.format(uFission))

# Increase radiation width and decrease fission width for 7.8 eV resonance
params.data[row][colG] += x*uCapture
params.data[row][colFA] -= x*uFission

print('MODIFIED RESONANCE PARAMETERS')
print(tabulate(params.data[4:6], headers=headers, tablefmt='grid') + '\n')

# Get capture and fission cross sections
print('Reconstructing resonances...')
eval.reconstructResonances()
capture = eval.getReaction('capture').getCrossSection()['linear']
fission = eval.getReaction('fission').getCrossSection()['linear']
newCapture2200 = capture.getValue(0.0253)
newFission2200 = fission.getValue(0.0253)
changeCapture = (newCapture2200 - originalCapture2200) / originalCapture2200
changeFission = (newFission2200 - originalFission2200) / originalFission2200
print('Modified 2200 m/s capture xs = {0:.3f} b ({1:.3%})'.format(newCapture2200, changeCapture))
print('Modified 2200 m/s fission xs = {0:.3f} b ({1:.3%})\n'.format(newFission2200, changeFission))

# ==============================================================================
header('(3) Modifying negative energy resonances...')
# ==============================================================================

# Determine 2200 m/s covariances for fission and capture
covFission = cov.sections[12]
uFission = covFission.getNativeData().getUncertaintyVector().getValue(0.0253)
covCapture = cov.sections[19]
uCapture = covCapture.getNativeData().getUncertaintyVector().getValue(0.0253)

print('Uncertainty in 2200 m/s capture = {0:.2f} eV ({1:.2%})'.format(
        uCapture*originalCapture2200, uCapture))
print('Uncertainty in 2200 m/s fission = {0:.2f} eV ({1:.2%})'.format(
        uFission*originalFission2200, uFission))

targetCapture = x*uCapture
targetFission = -x*uFission
print('Targeting a {0:.3%} increase in 2200 m/s capture'.format(targetCapture).upper())
print('Targeting a {0:.3%} decrease in 2200 m/s fission\n'.format(targetFission).upper())

initial_guess = 0.1
xg = initial_guess*uCapture
xf = initial_guess*uFission
iteration = 1
while True:
    print('Iteration ' + str(iteration))
    print('  Changing capture widths by {0:.1%}'.format(xg))
    print('  Changing fission widths by {0:.1%}'.format(xf))

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

    changeCapture = (capture2200 - newCapture2200) / newCapture2200
    changeFission = (fission2200 - newFission2200) / newFission2200
    print('  2200 m/s capture xs = {0:.3f} b ({1:.3%})'.format(capture2200, changeCapture))
    print('  2200 m/s fission xs = {0:.3f} b ({1:.3%})'.format(fission2200, changeFission))

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
print('\nMODIFIED RESONANCE PARAMETERS')
print(tabulate(params.data[:4], headers=headers, tablefmt='grid'))

# Get capture and fission cross sections
capture = eval.getReaction('capture').getCrossSection()['linear']
fission = eval.getReaction('fission').getCrossSection()['linear']
newCapture2200 = capture.getValue(0.0253)
newFission2200 = fission.getValue(0.0253)
changeCapture = (newCapture2200 - originalCapture2200) / originalCapture2200
changeFission = (newFission2200 - originalFission2200) / originalFission2200
print('Modified 2200 m/s capture xs = {0:.3f} b ({1:.3%})'.format(newCapture2200, changeCapture))
print('Modified 2200 m/s fission xs = {0:.3f} b ({1:.3%})\n'.format(newFission2200, changeFission))

# ==============================================================================
header('(4) Modifying thermal prompt nubar...')
# ==============================================================================

# Determine 2200 m/s covariance for nubar
covNubar = cov.sections[0]
uncvNubar = covNubar.getNativeData().getUncertaintyVector()
uNubar = uncvNubar.getValue(0.0253)

# Get prompt nubar
promptN = eval.getReaction('fission').outputChannel.particles[0]
nubar = promptN.multiplicity['pointwise']

print('Uncertainty in 2200 m/s prompt fission nubar = {0:.3f} ({1:.3%})\n'.format(
        uNubar*nubar.getValue(0.0253), uNubar))

# Set constants for modification
A = 1.0608
B = 2.3321

# Loop through energies and modified nu-bar values
for i, (energy, nu) in enumerate(nubar):
    nubar[i] = [energy, nu - x*uNubar*A*math.exp(-B*energy)]

# ==============================================================================
header('(5) Modifying prompt neutron fission spectra...')
# ==============================================================================

# Get prompt fission neutron spectrum from thermal fission
pnfs = promptN.distributions.components['uncorrelated'].energyComponent['pointwise']
xys = pnfs[0]
#x0, y0 = map(np.array, xys.copyDatatoXsAndYs())

# Construct Watt fission spectrum
a = 0.966e6
b = 2.842e-6
Watt = lambda E, a, b: float(np.exp(-E/a)*np.sinh(np.sqrt(b*E)))

# Uncertainty of 30 keV from R. Capote
uAverage = 30.0e3

originalAvgE = xys.integrateWithWeight_x()
origX, origY = xys.copyDataToXsAndYs()

print('Uncertainty in PFNS average energy = {0:.3f} keV ({1:.2%})'.format(
        uAverage/1e3, uAverage/originalAvgE))

target = x*uAverage/originalAvgE
initial_guess = 0.5
x = initial_guess*target
iteration = 0
print('Targeting a {0:.3%} increase in PFNS average energy ({1:.4f} MeV)'.format(
        target, originalAvgE*1e-6*(1 + target)).upper())

while True:
    print('Iteration ' + str(iteration))
    print('  Changing Watt parameter by {0:.2%}'.format(x))

    # Modify each probability by ratio of Watt spectra
    for i, (energy, prob) in enumerate(xys):
        if np.isclose(energy, 0.0):
            continue
        xys[i] = [energy, prob*Watt(energy, (1+x)*a, b)/Watt(energy, a, b)]

    # Renormalize spectra
    integral = xys.integrate()
    for i, (energy, prob) in enumerate(xys):
        xys[i] = [energy, prob/integral]

    avgE = xys.integrateWithWeight_x()
    change = (avgE - originalAvgE)/originalAvgE

    print('  PFNS average energy = {0:.4f} MeV ({1:.3%})'.format(
            avgE*1e-6, change))

    iteration += 1
    if (abs(target/change - 1) < abs(target)*0.1):
        break

    xys.setDataFromXsAndYs(origX, origY)
    x *= target/change

# ==============================================================================
header('(6) Writing new ENDF file...')
# ==============================================================================

captureXS = np.asarray(capture.copyDataToXsAndYs())
fissionXS = np.asarray(fission.copyDataToXsAndYs())

#interp = interp1d(originalCaptureXS[0], originalCaptureXS[1])
#orig = interp(captureXS[0])

#plt.loglog(originalCaptureXS[0], originalCaptureXS[1])
#plt.loglog(captureXS[0], (captureXS[1] - orig)/orig)
#plt.grid(True)
#plt.xlabel('Energy (eV)')
#plt.ylabel('Cross section (b)')
#plt.show()

# Plot data
#xm, ym = map(np.array, zip(*xys))
#plt.plot(x0, y0, label='Original')
#plt.plot(xm, ym, label='Modified')
#plt.show()

# Write out modified ENDF file
myENDF = eval.toENDF6({'verbosity': 0}, covarianceSuite=cov)
filename = 'modified.endf'
if len(sys.argv) > 1:
    directory = sys.argv[1]
    if not os.path.exists(directory):
        os.mkdir(directory)
    filename = os.path.join(directory, filename)
open(filename, 'w').write(myENDF)
