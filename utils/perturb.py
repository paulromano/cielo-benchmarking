#!/usr/bin/env python

import os
import argparse
from tkFileDialog import askopenfilename, asksaveasfilename
from Tkinter import Tk

from fudge.legacy.converting.endfFileToGND import endfFileToGND


def get_file():
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=[("All", "*"),])
    root.destroy()
    return filename

def perturb_reaction(data, reaction):
    choice = None
    choices = ['Add constant cross section',
               'Multiply by constant',
               'Multiply by fraction of covariance',
               'Return']
    while choice != len(choices):
        choice = get_choice(choices)
        if choice == 1:
            factor = eval(raw_input('How much to add (b)? '))
            if reaction.crossSection.nativeData == 'linear':
                crossSection = reaction.crossSection['linear']
                for i, (energy, value) in enumerate(crossSection):
                    crossSection[i] = [energy, value + factor]
            else:
                print("Can't perturb reaction with {} cross section".format(
                        reaction.crossSection.nativeData))
        elif choice == 2:
            factor = eval(raw_input('How factor to multiply by? '))
            if 'linear' in reaction.crossSection.forms:
                crossSection = reaction.crossSection['linear']
                for i, (energy, value) in enumerate(crossSection):
                    crossSection[i] = [energy, value*factor]
            else:
                print("Can't perturb reaction with {} cross section".format(
                        reaction.crossSection.nativeData))
        elif choice == 3:
            factor = eval(raw_input('What fraction of variance? '))
            pass

def perturb_cross_section(data):
    rs = data['reactionSuite']
    n = len(rs.reactions)

    choices = ['{} + {} --> {}'.format(rs.projectile, rs.target, r)
               for r in rs.reactions] + ['Return to main menu']
    choice = None
    while choice != len(choices):
        choice = get_choice(choices)
        if 0 < choice <= n:
            perturb_reaction(data, rs.reactions[choice - 1])

def save(data):
    root = Tk()
    root.withdraw()
    filename = asksaveasfilename()
    root.destroy()

    if filename:
        endf = data['reactionSuite'].toENDF6(
            {'verbosity': 0}, covarianceSuite=data['covarianceSuite'])
        open(filename, 'w').write(endf)

def get_choice(choices):
    os.system('clear')
    for i, choice in enumerate(choices):
        print('{}) {}'.format(i + 1, choice))
    return eval(raw_input('--> '))

def main(filename=None):
    # Prompt to load ENDF file
    if not filename:
        filename = get_file()
    print('Loading {}...'.format(filename))
    data = endfFileToGND(filename, toStdOut=False, toStdErr=False)

    choice = None
    choices = ['Perturb cross section',
               'Perturb fission neutron yield',
               'Perturb resonances',
               'Plot cross section',
               'Save new ENDF file',
               'Exit']
    while choice != len(choices):
        choice = get_choice(choices)
        if choice == 1:
            perturb_cross_section(data)
        elif choice == 2:
            pass
        elif choice == 3:
            pass
        elif choice == 4:
            pass
        elif choice == 5:
            save(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('endf', nargs='?', help='ENDF file', default=None)
    args = parser.parse_args()
    main(args.endf)
