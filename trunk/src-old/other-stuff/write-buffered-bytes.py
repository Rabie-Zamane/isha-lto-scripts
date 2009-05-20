'''
Created on 28-Apr-2009

@author: kevala
'''
from functools import partial

tape='/dev/nst0'
tarfile='/lto-stage/tapes/pending/t4/n-1-1-cam-1.tar'

INPUT = open(tarfile, 'rb')
OUTPUT = open(tape, 'wb')

buffsize = 64*512
for buff in iter(partial(INPUT.read, buffsize), ''):
    OUTPUT.write(buff)
    
INPUT.close()
OUTPUT.close()
     