#!/usr/bin/env python

import os
import subprocess
import sys

# Read lines from cross_sections_nndc.xml
lines = open('cross_sections_nndc.xml', 'r').readlines()

# Change working directory
if len(sys.argv) >= 1:
    os.chdir(sys.argv[1])

# Create full xsdir file
xsdir = open('xsdir', 'r').read()
xsdir = xsdir.replace('filename', '{}/ace'.format(os.getcwd())).replace('route', '0')
with open('xsdir_mod', 'w') as f:
    f.write('atomic weight ratios\ndirectory\n')
    f.write(xsdir)

# Convert xsdir file to XML
retcode = subprocess.call('~/openmc/src/utils/convert_xsdir.py xsdir_mod temp.xml', shell=True)
if retcode:
    raise Exception('Could not convert xsdir file')

# Get single line from XML file
replace_line = open('temp.xml', 'r').readlines()[3]
nuclide = replace_line.split('"')[1][:-4]

# Replace appropriate line in cross_sections.xml
for i, line in enumerate(lines):
    if nuclide in line:
        lines[i] = replace_line

# Write new cross_sections.xml file
open('cross_sections_new.xml', 'w').writelines(lines)

# Remove temporary files
os.remove('xsdir_mod')
os.remove('temp.xml')
