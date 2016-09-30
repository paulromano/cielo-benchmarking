#!/usr/bin/env python

import argparse
import os
import shutil
from subprocess import run, PIPE, STDOUT
import sys
import tempfile

import openmc.data

pendf_template = """
reconr / %%%%%%%%%%%%%%%%%%% Reconstruct XS for neutrons %%%%%%%%%%%%%%%%%%%%%%%
20 22
'ENDF/B-VII.1 PENDF for {zsymam}'/
{mat} 2/
0.001 0.0 0.003/ err tempr errmax
'ENDF/B-VII.1: {zsymam}'/
'Processed by NJOY2012.50'/
0/
stop
"""

ace_template = """
reconr / %%%%%%%%%%%%%%%%%%% Reconstruct XS for neutrons %%%%%%%%%%%%%%%%%%%%%%%
20 21
'ENDF/B-VII.1 PENDF for {zsymam}'/
{mat} 2/
0.001 0.0 0.003/ err tempr errmax
'ENDF/B-VII.1: {zsymam}'/
'Processed by NJOY2012.50'/
0/
broadr / %%%%%%%%%%%%%%%%%%%%%%% Doppler broaden XS %%%%%%%%%%%%%%%%%%%%%%%%%%%%
20 21 22
{mat} 1 0 0 0. /
0.001 -1.0e6 0.003 /
293.6
0/
heatr / %%%%%%%%%%%%%%%%%%%%%%%%% Add heating kerma %%%%%%%%%%%%%%%%%%%%%%%%%%%%
20 22 23 /
{mat} {num_partials} /
{heatr_partials} /
purr / %%%%%%%%%%%%%%%%%%%%%%%% Add probability tables %%%%%%%%%%%%%%%%%%%%%%%%%
20 23 24
{mat} 1 5 20 64 /
293.6
1.e10 1.e4 1.e3 1.e2 1.e1
0/
acer / %%%%%%%%%%%%%%%%%%%%%%%%%%%%% Make ACE file %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
20 24 0 25 26
1 0 1 .01 /
'ENDF/B-VII.1: {zsymam} processed by NJOY2012.50'/
{mat} 293.6
1 1/
/
stop
"""

def make_pendf(filename, output=None):
    ev = openmc.data.endf.Evaluation(filename)
    mat = ev.material
    zsymam = ev.target['zsymam']

    with tempfile.TemporaryDirectory() as tmpdirname:
        # Copy evaluation to tape20
        shutil.copy(filename, os.path.join(tmpdirname, 'tape20'))

        commands = pendf_template.format(**locals())
        njoy = run(['njoy'], cwd=tmpdirname, input=commands, stdout=PIPE,
                   stderr=STDOUT, universal_newlines=True)
        if njoy.returncode != 0:
            print('Failed to produce PENDF for {}'.format(filename))

        if output is None:
            output = zsymam.replace(' ', '') + '.pendf'

        pendf_file = os.path.join(tmpdirname, 'tape22')
        if os.path.isfile(pendf_file):
            shutil.move(pendf_file, output)

    return njoy


def make_ace(filename, output=None, show_output=True):
    ev = openmc.data.endf.Evaluation(filename)
    mat = ev.material
    zsymam = ev.target['zsymam']

    with tempfile.TemporaryDirectory() as tmpdirname:
        # Copy evaluation to tape20
        shutil.copy(filename, os.path.join(tmpdirname, 'tape20'))

        # Determine which partial heating values are needed to self-shield heating
        # for ptables
        partials = [302, 402]
        if ev.target['fissionable']:
            partials.append(318)
        heatr_partials = ' '.join(map(str, partials))
        num_partials = len(partials)

        commands = ace_template.format(**locals())
        njoy = run(['njoy'], cwd=tmpdirname, input=commands, stdout=PIPE,
                   stderr=STDOUT, universal_newlines=True)
        if njoy.returncode != 0:
            print('Failed to produce ACE for {}'.format(filename))

        if output is None:
            output = zsymam.replace(' ', '') + '.ace'
        output_xsdir = zsymam.replace(' ', '') + '.xsdir'

        ace_file = os.path.join(tmpdirname, 'tape25')
        xsdir_file = os.path.join(tmpdirname, 'tape26')
        if os.path.exists(ace_file):
            shutil.move(ace_file, output)
        if os.path.exists(xsdir_file):
            shutil.move(xsdir_file, output_xsdir)

    # Write NJOY output
    open(zsymam.replace(' ', '') + '.njo', 'w').write(njoy.stdout)

    return njoy


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='Path to ENDF file')
    args = parser.parse_args()

    make_ace(args.filename)
