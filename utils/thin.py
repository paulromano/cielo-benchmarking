#!/usr/bin/env python

import argparse
import struct
import numpy as np
import matplotlib.pyplot as plt

import warnings
with warnings.catch_warnings():
    from pyne.utils import VnVWarning
    warnings.filterwarnings("ignore", category=VnVWarning)
    import pyne.ace

parser = argparse.ArgumentParser()
parser.add_argument('ace', action='store', help='ACE file to thin')
parser.add_argument('-t', '--tol', dest='tol', action='store', type=float,
                    default=0.01, help='tolerance for thinning')
args = parser.parse_args()

# ==============================================================================
# Read data from ACE file
lib = pyne.ace.Library(args.ace)
lib.read()
o16 = lib.tables.values()[0]
elastic = o16.reactions[2]
ad = elastic.angular_distribution
E = ad.energy

# Determine average scattering cosine at each incident energy
print ('Generating average mu...')
avgmu = np.zeros_like(E)
mu = np.linspace(-1., 1., 10000)
for i in range(len(E)):
    p = np.interp(mu, ad.cosine[i], ad.pdf[i])
    avgmu[i] = sum(np.diff(mu)*(p[1:] + p[:-1])*(mu[1:] + mu[:-1])/4)

# Perform thinning on energy grid based on change in 1st-order Legendre moment
print('Thinning energy grid...')
i = 0
keep = [i]
j = 2
while True:
    interp = avgmu[i] + (avgmu[i+j] - avgmu[i])/(E[i+j] - E[i])*(
        E[i+1:i+j] - E[i])
    true = avgmu[i+1:i+j]
    err = abs(interp - true)
    if np.any(err > args.tol):
        keep.append(i + j - 1)
        i += j - 1
        j = 2
    else:
        j += 1
        if i + j == len(E):
            keep.append(i + j - 1)
            break
keep = np.array(keep)

plt.semilogx(E, avgmu, 'b.')
plt.semilogx(E[keep], avgmu[keep], 'ko')
plt.show()

print('Original = {}'.format(len(E)))
print('Thinned  = {}'.format(len(keep)))

# ==============================================================================
# MODIFY ACE FILE AND WRITE AS BINARY

# Read data from ASCII file
ascii = open(args.ace, 'r')
lines = ascii.readlines()
ascii.close()

# Set default record length
record_length = 4096

# Open binary file
binary = open(args.ace + '.thinned', 'wb')

idx = 0
while idx < len(lines):
    # Read/write header block
    hz = lines[idx][:10].encode('UTF-8')
    aw0 = float(lines[idx][10:22])
    tz = float(lines[idx][22:34])
    hd = lines[idx][35:45].encode('UTF-8')
    hk = lines[idx + 1][:70].encode('UTF-8')
    hm = lines[idx + 1][70:80].encode('UTF-8')
    binary.write(struct.pack(str('=10sdd10s70s10s'), hz, aw0, tz, hd, hk, hm))

    # Read/write IZ/AW pairs
    data = ' '.join(lines[idx + 2:idx + 6]).split()
    iz = list(map(int, data[::2]))
    aw = list(map(float, data[1::2]))
    izaw = [item for sublist in zip(iz, aw) for item in sublist]
    binary.write(struct.pack(str('=' + 16*'id'), *izaw))

    # Read/write NXS and JXS arrays. Null bytes are added at the end so
    # that XSS will start at the second record
    nxs = list(map(int, ' '.join(lines[idx + 6:idx + 8]).split()))
    jxs = list(map(int, ' '.join(lines[idx + 8:idx + 12]).split()))
    binary.write(struct.pack(str('=16i32i{0}x'.format(record_length - 500)),
                             *(nxs + jxs)))

    # Read/write XSS array. Null bytes are added to form a complete record
    # at the end of the file
    n_lines = (nxs[0] + 3)//4
    xss = list(map(float, ' '.join(lines[
        idx + 12:idx + 12 + n_lines]).split()))

    # Modify angular distributions
    idx = jxs[8] - 1
    LC = xss[idx + 1 + len(E):idx + 1 + 2*len(E)]
    ne = len(keep)
    xss[idx] = ne
    for i in range(ne):
        xss[idx + 1 + i] = E[keep[i]]
        xss[idx + 1 + ne + i] = LC[keep[i]]

    extra_bytes = record_length - ((len(xss)*8 - 1) % record_length + 1)
    binary.write(struct.pack(str('={0}d{1}x'.format(nxs[0], extra_bytes)),
                             *xss))

    # Advance to next table in file
    idx += 12 + n_lines

# Close binary file
binary.close()
