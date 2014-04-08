#!/usr/bin/env python

import copy

import matplotlib.pyplot as plt
import numpy as np
from fudge.legacy.converting.endfFileToGND import endfFileToGND

# File to convert
endffile = 'endf-b-vii-1.endf'

# This is the "change" parameter by which all data is adjusted
x = 0.05

# ==============================================================================
# Create ReactionSuite from ENDF file
print('Reading data from {0}...'.format(endffile))
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
print('Modifying resonance parameters...')

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

# Increase radiation width for 0.3 eV resonance
uFission = 0.019
uCapture = 0.042
resonance = 0.2956243
row = energy.index(resonance)
params.data[row][colG] *= 1 + x*uCapture

# Decrease fission widths for 0.3 eV resonance -- note that for both this
# resonance and the 7.8 eV resonance, the second-chance fission partial-width is
# zero already so it doesn't need to be adjusted
params.data[row][colFA] *= 1 - x*uFission

# Increase radiation width for 7.8 eV resonance
uCapture = 0.071
uFission = 0.03
resonance = 7.8158
row = energy.index(resonance)
params.data[row][colG] *= 1 + x*uCapture

# Decrease fission widths for 7.8 eV resonance
params.data[row][colFA] *= 1 - x*uFission

# ==============================================================================
print('Modifying prompt neutron fission spectra...')

# Get fission reaction
fission = eval.getReaction('fission')

# Get prompt fission neutron spectrum from thermal fission
pnfs = fission.outputChannel.particles[0].distributions. \
    components['uncorrelated'].energyComponent['pointwise']
xys = pnfs[0]
#x0, y0 = map(np.array, xys.copyDatatoXsAndYs())

# Construct Watt fission spectrum
a = 0.966e6
b = 2.842e-6
Watt = lambda E, a, b: float(np.exp(-E/a)*np.sinh(np.sqrt(b*E)))

# Modify each probability by ratio of Watt spectra
for i, (energy, prob) in enumerate(xys):
    if np.isclose(energy, 0.0):
        continue
    xys[i] = [energy, prob*Watt(energy, (1+x)*a, b)/Watt(energy, a, b)]

# Renormalize spectra
integral = xys.integrate()
for i, (energy, prob) in enumerate(xys):
    xys[i] = [energy, prob/integral]


# ==============================================================================

# Plot data
#xm, ym = map(np.array, zip(*xys))
#plt.plot(x0, y0, label='Original')
#plt.plot(xm, ym, label='Modified')
#plt.show()

# Write out modified ENDF file
myENDF = eval.toENDF6({'verbosity': 0}, covarianceSuite=cov)
open('junk.endf', 'w').write(myENDF)
