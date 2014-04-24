#!/usr/bin/env python

from __future__ import print_function
import copy
import math

import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate
from fudge.legacy.converting.endfFileToGND import endfFileToGND

# File to convert
endffile = 'endf-b-vii-1.endf'

# This is the "change" parameter by which all data is adjusted
x = 0.05

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

# Get RM parameters
params = eval.resonances.resolved.regions[0].nativeData.resonanceParameters

# Get energy column and column indices for partial-widths
energy = params.getColumn('energy')
columnNames = [col.name for col in params.columns]
colN = columnNames.index('neutronWidth')
colG = columnNames.index('captureWidth')
colFA = columnNames.index('fissionWidthA')
colFB = columnNames.index('fissionWidthB')

# ==============================================================================
header('(2) Modifying resonance parameters...')
# ==============================================================================

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

headers = [col.name + (' ({0})'.format(col.units) if col.units else '')
          for col in params.columns]

originalData = copy.deepcopy(params.data)
print('ORIGINAL RESONANCE PARAMETERS')
print(tabulate(originalData[4:6], headers=headers, tablefmt='grid') + '\n')

uFission = 0.019
uCapture = 0.042
resonance = 0.2956243
row = energy.index(resonance)
print('Uncertainty in 0.296 eV capture width = {0} eV'.format(
        uCapture*params.data[row][colG]))
print('Uncertainty in 0.296 eV fissionA width = {0} eV'.format(
        uFission*params.data[row][colFA]))

# Increase radiation width for 0.3 eV resonance and decrease fission widths for
# 0.3 eV resonance -- note that for both this resonance and the 7.8 eV
# resonance, the second-chance fission partial-width is zero already so it
# doesn't need to be adjusted
params.data[row][colG] *= 1 + x*uCapture
params.data[row][colFA] *= 1 - x*uFission

uCapture = 0.071
uFission = 0.03
resonance = 7.8158
row = energy.index(resonance)
print('Uncertainty in 7.8 eV capture width = {0} eV'.format(
        uCapture*abs(params.data[row][colG])))
print('Uncertainty in 7.8 eV fissionA width = {0} eV\n'.format(
        uFission*abs(params.data[row][colFA])))

# Increase radiation width and decrease fission width for 7.8 eV resonance
params.data[row][colG] *= 1 + x*uCapture
params.data[row][colFA] *= 1 - x*uFission

print('MODIFIED RESONANCE PARAMETERS')
print(tabulate(params.data[4:6], headers=headers, tablefmt='grid') + '\n')

# ==============================================================================
header('(3) Modifying thermal prompt nubar...')
# ==============================================================================

# Determine 2200 m/s covariance for nubar
covNubar = cov.sections[0]
uncvNubar = covNubar.getNativeData().getUncertaintyVector()
uNubar = uncvNubar.getValue(0.0253)
print('Uncertainty in 2200 m/s prompt fission nubar = {0:.3f}%'.format(
        uNubar*100))

# Get prompt nubar
fission = eval.getReaction('fission')
promptN = fission.outputChannel.particles[0]
nubar = promptN.multiplicity['pointwise']

# Set constants for modification
A = 1.0608
B = 2.3321

# Loop through energies and modified nu-bar values
for i, (energy, nu) in enumerate(nubar):
    nubar[i] = [energy, nu - x*uNubar*A*math.exp(-B*energy)]

# ==============================================================================
header('(4) Modifying prompt neutron fission spectra...')
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

target = x*uAverage/originalAvgE
initial_guess = 0.5
x = initial_guess*target
iteration = 0
print('Targeting a {0:.3f}% increase in PFNS average energy ({1:.4f} MeV)'.format(
        target*100, originalAvgE*1e-6*(1 + target)).upper())

while True:
    print('Iteration ' + str(iteration))
    print('  Changing Watt parameter by {0:.2f}%'.format(x*100))

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

    print('  PFNS average energy = {0:.4f} MeV ({1:.3f}%)'.format(
            avgE*1e-6, change*100))

    iteration += 1
    if (abs(target/change - 1) < abs(target)*0.1):
        break

    xys.setDataFromXsAndYs(origX, origY)
    x *= target/change


# ==============================================================================

# Plot data
#xm, ym = map(np.array, zip(*xys))
#plt.plot(x0, y0, label='Original')
#plt.plot(xm, ym, label='Modified')
#plt.show()

# Write out modified ENDF file
myENDF = eval.toENDF6({'verbosity': 0}, covarianceSuite=cov)
open('junk.endf', 'w').write(myENDF)
