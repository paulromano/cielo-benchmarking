#!/usr/bin/env python

import sys

import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from fudge.legacy.converting.endfFileToGND import endfFileToGND

plotfunc = {('lin', 'lin'): plt.plot, ('lin', 'log'): plt.semilogy,
            ('log', 'lin'): plt.semilogx, ('log', 'log'): plt.loglog}

def plot_cross_section(xs1, xs2, xlabel='Energy (eV)', ylabel='Cross section (b)',
                       xscale='log', yscale='log'):
    plotfunc[xscale, yscale](xs1[0], xs1[1])
    plotfunc[xscale, yscale](xs2[0], xs2[1])
    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()
    plt.close()

def plot_diff(xs1, xs2, xlabel='Energy (eV)', ylabel='Difference (b)',
              xscale='log', yscale='lin', uncertainty=None):
    f = interp1d(*xs2)
    plotfunc[xscale, yscale](xs1[0], f(xs1[0]) - xs1[1])
    if uncertainty:
        plotfunc[xscale, yscale](uncertainty[0], uncertainty[1], 'k--')
    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()
    plt.close()

def plot_relative_diff(xs1, xs2, xlabel='Energy (eV)', ylabel='Relative difference',
                       xscale='log', yscale='lin', uncertainty=None):
    f = interp1d(*xs2)
    plotfunc[xscale, yscale](xs1[0], abs(f(xs1[0]) - xs1[1])/xs1[1])
    if uncertainty:
        plotfunc[xscale, yscale](uncertainty[0], uncertainty[1], 'k--')
    plt.grid(True, which='both', color='lightgray', ls='-', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()
    plt.close()


file1 = sys.argv[1]
file2 = sys.argv[2]

t1 = endfFileToGND(file1, toStdOut=False, toStdErr=False)
t2 = endfFileToGND(file2, toStdOut=False, toStdErr=False)
eval1 = t1['reactionSuite']
cov   = t1['covarianceSuite']
eval2 = t2['reactionSuite']

# Reconstruct resonance
eval1.reconstructResonances()
eval2.reconstructResonances()

# Get cross sections
capture_xs1 = eval1.getReaction('capture').getCrossSection()['linear'].copyDataToXsAndYs()
capture_xs2 = eval2.getReaction('capture').getCrossSection()['linear'].copyDataToXsAndYs()
capture_unc = cov.sections[19].getNativeData().getUncertaintyVector().copyDataToXsAndYs()
fission_xs1 = eval1.getReaction('fission').getCrossSection()['linear'].copyDataToXsAndYs()
fission_xs2 = eval2.getReaction('fission').getCrossSection()['linear'].copyDataToXsAndYs()
fission_unc = cov.sections[12].getNativeData().getUncertaintyVector().copyDataToXsAndYs()
plot_cross_section(capture_xs1, capture_xs2)
plot_diff(capture_xs1, capture_xs2)
plot_relative_diff(capture_xs1, capture_xs2, uncertainty=capture_unc)
plot_cross_section(fission_xs1, fission_xs2)
plot_diff(fission_xs1, fission_xs2)
plot_relative_diff(fission_xs1, fission_xs2, uncertainty=fission_unc)

prompt1 = eval1.getReaction('fission').outputChannel.particles[0]
prompt2 = eval2.getReaction('fission').outputChannel.particles[0]
nubar1 = prompt1.multiplicity['pointwise'].copyDataToXsAndYs()
nubar2 = prompt2.multiplicity['pointwise'].copyDataToXsAndYs()
nubar_unc = cov.sections[0].getNativeData().getUncertaintyVector().copyDataToXsAndYs()
plot_cross_section(nubar1, nubar2, ylabel='Prompt nubar', yscale='lin')
plot_diff(nubar1, nubar2, ylabel='Difference')
plot_relative_diff(nubar1, nubar2, uncertainty=nubar_unc)

pfns1 = prompt1.distributions.components['uncorrelated'].\
    energyComponent['pointwise'].getAtEnergy(1e-5).copyDataToXsAndYs()
pfns2 = prompt2.distributions.components['uncorrelated'].\
    energyComponent['pointwise'].getAtEnergy(1e-5).copyDataToXsAndYs()
plot_cross_section(pfns1, pfns2, ylabel='Probability', yscale='lin')
plot_diff(pfns1, pfns2, ylabel='Difference')
plot_relative_diff(pfns1, pfns2)
