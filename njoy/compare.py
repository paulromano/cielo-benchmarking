#!/usr/bin/env python

import argparse
import os
import openmc.data
import matplotlib.pyplot as plt
import numpy as np

from njoy import make_pendf


def compare(filename, plot=False, mt=2):
    # Use NJOY/RECONR to reconstruct resonances
    make_pendf(filename, 'pendf')
    try:
        njoy = openmc.data.IncidentNeutron.from_endf('pendf')
    except:
        print("Couldn't read PENDF {}".format(filename))
        return

    omc = openmc.data.IncidentNeutron.from_endf(filename)
    fissionable = 18 in omc.reactions

    for i_rrr, rrr in enumerate(omc.resonances):
        if rrr is None or type(rrr) is openmc.data.ResonanceRange:
            print('{}: No resolved resonances'.format(omc.name))
            return
        elif isinstance(rrr, openmc.data.RMatrixLimited):
            print('{}: R-Matrix limited not supported'.format(omc.name))
            return
        elif isinstance(rrr, openmc.data.Unresolved):
            continue

        # Get range of resolved resonances
        e_min = rrr.energy_min
        e_max = rrr.energy_max

        # Get energies on PENDF which are within range
        xs_elastic = njoy[2].xs['0K']
        xs_capture = njoy[102].xs['0K']
        if fissionable:
            xs_fission = njoy[18].xs['0K']
        energies = xs_elastic.x[(e_min <= xs_elastic.x) & (xs_elastic.x < e_max)]

        njoy_xs = {}
        njoy_xs[2] = xs_elastic(energies)
        njoy_xs[102] = xs_capture(energies)
        if fissionable:
            njoy_xs[18] = xs_fission(energies)

        # Reconstruct using openmc.data
        omc_xs = rrr.reconstruct(energies)
        omc_xs[2] += omc[2].xs['0K'].background(energies)
        omc_xs[102] += omc[102].xs['0K'].background(energies)
        if fissionable:
            omc_xs[18] += omc[18].xs['0K'].background(energies)

        if np.any(omc_xs[mt] < 0.0):
            print('Warning: negative cross sections for {}'.format(omc.name))

        # Plot differences
        rel_diff_2 = (njoy_xs[2] - omc_xs[2])/njoy_xs[2]
        rel_diff_102 = (njoy_xs[102] - omc_xs[102])/njoy_xs[102]
        if fissionable:
            rel_diff_18 = (njoy_xs[18] - omc_xs[18])/njoy_xs[18]

        i = abs(rel_diff_2).argmax()
        print('{} MT2 = {:.2%} at E={}, xs={} ({})'.format(
            omc.name, max(abs(rel_diff_2)), energies[i], njoy_xs[2][i], type(rrr)))

        i = abs(rel_diff_102).argmax()
        print('{} MT102 = {:.2%} at E={}, xs={}'.format(
            omc.name, max(abs(rel_diff_102)), energies[i], njoy_xs[102][i]))

        if fissionable:
            i = abs(rel_diff_2).argmax()
            print('{} MT18 = {:.2%} at E={}, xs={}'.format(
                omc.name, max(abs(rel_diff_18)), energies[i], njoy_xs[18][i]))

        if plot:
            if not os.path.isdir('plots'):
                os.mkdir('plots')

            plt.semilogx(energies, rel_diff_2, label='elastic')
            plt.semilogx(energies, rel_diff_102, label='capture')
            if fissionable:
                plt.semilogx(energies, rel_diff_18, label='fission')
            #plt.ylim((-1e-4, 1e-4))
            plt.legend(loc='best')
            plt.savefig('plots/{}_{}.png'.format(omc.name, i_rrr))
            plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='+', help='Path to ENDF file')
    parser.add_argument('-p', '--plot', action='store_true', help='Show plot of cross sections and differences')
    args = parser.parse_args()

    for f in args.filename:
        compare(f, args.plot, 2)
