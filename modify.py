#!/usr/bin/env python

from __future__ import print_function
import argparse
import copy
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from tabulate import tabulate
from fudge.legacy.converting.endfFileToGND import endfFileToGND

def header(s):
    n = (77 - len(s))//2
    print('{0}\n{1} {2} {1}\n{0}\n'.format(
            '='*79, ' '*n, s, ' '*(79 - n+len(s)+2)))

class Evaluation(object):
    def __init__(self, filename, target):
        self.target = target
        print('Target: {0}\n'.format(target))

        header('Reading data from {0}'.format(filename))
        self.endf = endfFileToGND(filename, toStdOut=False, toStdErr=False)

        # Store original 2200 m/s values for capture and fission
        self.capture = []
        self.fission = []
        self._get_2200_values()

        # Get original RM parameters
        rSuite = self.endf['reactionSuite']
        resolvedResonances = rSuite.resonances.resolved
        if resolvedResonances.multipleRegions:
            params = resolvedResonances.regions[0].nativeData.resonanceParameters
        else:
            params = resolvedResonances.nativeData.resonanceParameters
        columnNames = [col.name for col in params.columns]
        self.headers = [col.name + (' ({0})'.format(col.units) if col.units else '')
                   for col in params.columns]
        print('ORIGINAL RESONANCE PARAMETERS')
        row = np.where(np.array(params.getColumn('energy')) > 0.)[0][0]
        print(tabulate(params.data[:row+2], headers=self.headers, tablefmt='grid') + '\n')

    def _get_2200_values(self):
        print('Reconstructing resonances...')
        rSuite = self.endf['reactionSuite']
        rSuite.reconstructResonances()
        self.capture.append(rSuite.getReaction('capture')\
                                .getCrossSection()['linear'].getValue(0.0253))
        self.fission.append(rSuite.getReaction('fission')\
                                .getCrossSection()['linear'].getValue(0.0253))

    def modify_lowE_resonances(self, args):
        # Get capture and fission cross sections
        print('Original 2200 m/s capture xs = {0:.3f} b'.format(self.capture[0]))
        print('Original 2200 m/s fission xs = {0:.3f} b'.format(self.fission[0]))

        # Get RM parameters, column indices for partial-widths
        rSuite = self.endf['reactionSuite']
        resolvedResonances = rSuite.resonances.resolved
        if resolvedResonances.multipleRegions:
            params = resolvedResonances.regions[0].nativeData.resonanceParameters
        else:
            params = resolvedResonances.nativeData.resonanceParameters
        columnNames = [col.name for col in params.columns]
        colE = columnNames.index('energy')
        colN = columnNames.index('neutronWidth')
        colG = columnNames.index('captureWidth')
        colFA = columnNames.index('fissionWidthA')
        colFB = columnNames.index('fissionWidthB')

        header('Modifying resonance parameters...')

        # Uncertainties in resonance parameters given by Gilles Noguerre. These are
        # supposedly from SG34 file 32.

        if args.capture_03 or args.fission_03:
            uCapture = 1.3e-3
            uFission = 0.95e-3
            row = np.where(np.array(params.getColumn('energy')) > 0.)[0][0]
            print('Uncertainty in 0.296 eV capture width = {0} eV'.format(uCapture))
            print('Uncertainty in 0.296 eV fissionA width = {0} eV'.format(uFission))

            # Increase radiation width / decrease fission widths 
            if args.capture_03:
                params.data[row][colG] += self.target*uCapture
            if args.fission_03:
                params.data[row][colFA] -= self.target*uFission

        if args.capture_78 or args.fission_78:
            uCapture = 2.1e-3
            uFission = 1.85e-3
            row = np.where(np.array(params.getColumn('energy')) > 0.)[0][0] + 1
            print('Uncertainty in 7.8 eV capture width = {0} eV'.format(uCapture))
            print('Uncertainty in 7.8 eV fissionA width = {0} eV\n'.format(uFission))

            # Increase radiation width / decrease fission widths 
            if args.capture_78:
                params.data[row][colG] += self.target*uCapture
            if args.fission_78:
                params.data[row][colFA] -= self.target*uFission

        print('MODIFIED RESONANCE PARAMETERS')
        row = np.where(np.array(params.getColumn('energy')) > 0.)[0][0]
        print(tabulate(params.data[row:row+2], headers=self.headers, tablefmt='grid') + '\n')

        # Get capture and fission cross sections
        self._get_2200_values()
        changeCapture = (self.capture[-1] - self.capture[0]) / self.capture[0]
        changeFission = (self.fission[-1] - self.fission[0]) / self.fission[0]
        print('Modified 2200 m/s capture xs = {0:.3f} b ({1:.3%})'.format(self.capture[-1], changeCapture))
        print('Modified 2200 m/s fission xs = {0:.3f} b ({1:.3%})\n'.format(self.fission[-1], changeFission))

    def modify_negative_resonances(self):
        header('Modifying negative energy resonances...')
        rSuite = self.endf['reactionSuite']
        resolvedResonances = rSuite.resonances.resolved
        if resolvedResonances.multipleRegions:
            params = resolvedResonances.regions[0].nativeData.resonanceParameters
        else:
            params = resolvedResonances.nativeData.resonanceParameters

        columnNames = [col.name for col in params.columns]
        colN = columnNames.index('neutronWidth')
        colG = columnNames.index('captureWidth')
        colFA = columnNames.index('fissionWidthA')
        colFB = columnNames.index('fissionWidthB')
        headers = [col.name + (' ({0})'.format(col.units) if col.units else '')
                   for col in params.columns]

        # Determine 2200 m/s covariances for fission and capture
        cSuite = self.endf['covarianceSuite']
        try:
            covFission = cSuite.sections[12]
            uFission = covFission.getNativeData().getUncertaintyVector().getValue(0.0253)
        except IndexError:
            uFission = 0.011260977

        try:
            covCapture = cSuite.sections[19]
            uCapture = covCapture.getNativeData().getUncertaintyVector().getValue(0.0253)
        except IndexError:
            uCapture = 0.017603641

        print('Uncertainty in 2200 m/s capture = {0:.2f} b ({1:.2%})'.format(
                uCapture*self.capture[0], uCapture))
        print('Uncertainty in 2200 m/s fission = {0:.2f} b ({1:.2%})'.format(
                uFission*self.fission[0], uFission))

        targetCapture = self.target*uCapture
        targetFission = -self.target*uFission
        print('Targeting a {0:.3%} increase in 2200 m/s capture'.format(targetCapture).upper())
        print('Targeting a {0:.3%} decrease in 2200 m/s fission\n'.format(targetFission).upper())

        # Determine number of negative resonances
        n_res = np.where(np.array(params.getColumn('energy')) < 0.)[0].size

        initial_guess = 0.2
        xg = initial_guess*uCapture
        xf = initial_guess*uFission
        iteration = 1
        j = len(self.capture) - 1
        while True:
            print('Iteration ' + str(iteration))
            print('  Changing capture widths by {0:.1%}'.format(xg))
            print('  Changing fission widths by {0:.1%}'.format(xf))

            # Save original values
            GG = [params.data[i][colG] for i in range(n_res)]
            GFA = [params.data[i][colFA] for i in range(n_res)]
            GFB = [params.data[i][colFB] for i in range(n_res)]

            # Increase capture widths and decrease fission widths for negative energy
            # resonances -- note that if the width is negative, we do the opposite
            for row in range(n_res):
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
            self._get_2200_values()

            changeCapture = (self.capture[-1] - self.capture[j]) / self.capture[j]
            changeFission = (self.fission[-1] - self.fission[j]) / self.fission[j]
            print('  2200 m/s capture xs = {0:.3f} b ({1:.3%})'.format(self.capture[-1], changeCapture))
            print('  2200 m/s fission xs = {0:.3f} b ({1:.3%})'.format(self.fission[-1], changeFission))

            iteration += 1
            if (abs(targetCapture/changeCapture - 1) < abs(targetCapture)*0.1 and
                abs(targetFission/changeFission - 1) < abs(targetFission)*0.1):
                break

            # Reset partial widths
            for row in range(n_res):
                params.data[row][colG] = GG[row]
                params.data[row][colFA] = GFA[row]
                params.data[row][colFB] = GFB[row]

            xg *= targetCapture/changeCapture
            xf *= targetFission/changeFission

        # Print tables
        print('\nMODIFIED RESONANCE PARAMETERS')
        print(tabulate(params.data[:n_res], headers=self.headers, tablefmt='grid'))

        # Get capture and fission cross sections
        changeCapture = (self.capture[-1] - self.capture[0]) / self.capture[0]
        changeFission = (self.fission[-1] - self.fission[0]) / self.fission[0]
        print('Modified 2200 m/s capture xs = {0:.3f} b ({1:.3%})'.format(self.capture[-1], changeCapture))
        print('Modified 2200 m/s fission xs = {0:.3f} b ({1:.3%})\n'.format(self.fission[-1], changeFission))


    def modify_nubar(self):

        header('Modifying thermal prompt nubar...')

        # Determine 2200 m/s covariance for nubar
        try:
            covNubar = self.endf['covarianceSuite'].sections[0]
            uncvNubar = covNubar.getNativeData().getUncertaintyVector()
            uNubar = uncvNubar.getValue(0.0253)
        except IndexError:
            uNubar = 0.0018568252

        # Get prompt nubar
        nubar = self.endf['reactionSuite'].getReaction('fission').outputChannel\
            .particles[0].multiplicity['pointwise']

        print('Uncertainty in 2200 m/s prompt fission nubar = {0:.3f} ({1:.3%})\n'.format(
                uNubar*nubar.getValue(0.0253), uNubar))

        # Set constants for modification
        A = 1.0608
        B = 2.3321

        # Loop through energies and modified nu-bar values
        for i, (energy, nu) in enumerate(nubar):
            nubar[i] = [energy, nu - self.target*uNubar*A*math.exp(-B*energy)]

    def modify_fission_spectrum(self):
        header('Modifying prompt neutron fission spectra...')

        # Get prompt fission neutron spectrum from thermal fission
        promptN = self.endf['reactionSuite'].getReaction('fission').outputChannel.particles[0]
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

        target = self.target*uAverage/originalAvgE
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

    def write(self, filename):
        header('Writing new ENDF file...')
        endf = self.endf['reactionSuite'].toENDF6(
            {'verbosity': 0}, covarianceSuite=self.endf['covarianceSuite'])
        open(filename, 'w').write(endf)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('endf', help='ENDF file to modify')
    parser.add_argument('endfModified', help='Modified ENDF file')
    parser.add_argument('target', type=float, help='Target percentage change')
    parser.add_argument('--capture-03', action='store_true', help='Increase 0.3 eV capture width')
    parser.add_argument('--fission-03', action='store_true', help='Decrease 0.3 eV fission width')
    parser.add_argument('--capture-78', action='store_true', help='Increase 7.8 eV capture width')
    parser.add_argument('--fission-78', action='store_true', help='Decrease 7.8 eV fission width')
    parser.add_argument('--negative', action='store_true', help='Modify negative energy resonances')
    parser.add_argument('--nubar', action='store_true', help='Modify nubar')
    parser.add_argument('--pfns', action='store_true', help='Modify prompt fission neutron spectrum')
    args = parser.parse_args()

    # Read evaluation
    pu239 = Evaluation(args.endf, args.target)

    # Make modifications
    lowE = (args.capture_03 or args.fission_03 or args.capture_78 or args.fission_78)
    if lowE: pu239.modify_lowE_resonances(args)
    if args.negative: pu239.modify_negative_resonances()
    if args.nubar: pu239.modify_nubar()
    if args.pfns: pu239.modify_fission_spectrum()

    # Write modified evaluation
    pu239.write(args.endfModified)
