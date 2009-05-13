'''
Created on 13-May-2009

@author: kevala
'''

import lto_util
import timeit

def main():

    print timeit.Timer('import lto_util\nprint lto_util.compare("/lto-stage/temp/test1.rdm", "/lto-stage/temp/test2.rdm")').timeit(1)
    


if __name__ == "__main__":
    main()
