#!/usr/bin/env python

from fudge.legacy.converting.endfFileToGND import endfFileToGND

# This is the "change" parameter by which all data is adjusted
x = 0.05

# Create ReactionSuite from ENDF file
eval, cov = endfFileToGND('n-094_Pu_239.endf')

# Get RM parameters
params = eval.resonances.resolved.regions[0].nativeData.resonanceParameters

# Get energy column and column indices for partial-widths
energy = params.getColumn('energy')
columnNames = [col.name for col in params.columns]
colN = columnNames.index('neutronWidth')
colFA = columnNames.index('fissionWidthA')
colFB = columnNames.index('fissionWidthB')

# Increase radiation width for 0.3 eV resonance
resonance = 0.2956243
row = energy.index(resonance)
params.data[row][colN] *= 1 + x

# Decrease fission widths for 0.3 eV resonance -- note that for both this
# resonance and the 7.8 eV resonance, the second-chance fission partial-width is
# zero already so it doesn't need to be adjusted
params.data[row][colFA] *= 1 - x

# Increase radiation width for 7.8 eV resonance
resonance = 7.8158
row = energy.index(resonance)
params.data[row][colN] *= 1 + x

# Decrease fission widths for 7.8 eV resonance
params.data[row][colFA] *= 1 - x

# Write out modified ENDF file
myENDF = eval.toENDF6({'verbosity': 0}, covarianceSuite=cov)
open('junk.endf', 'w').write(myENDF)
