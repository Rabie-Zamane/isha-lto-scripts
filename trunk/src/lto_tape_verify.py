'''
Created on 04-May-2009

@author: kevala
'''

import optparse
import sys
import os
import xml.dom.minidom
import ConfigParser 
import lto_util
import lto_write_util
import lto_verify_util


def main():

    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-i", "--tape-id", dest="tape_id", type="string", help="Specify tape id")
    (options, args) = parser.parse_args()
    
    lto_write_util.check_write_args(options)
    tape_id = options.tape_id
    
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    
    lto_util.config_checks(config)
    lto_util.path_check(lto_util.get_tape_written_dir(config)+'/'+tape_id)
    lto_util.delete_dir_content(lto_util.get_tape_verify_dir(config))
    
    lto_write_util.setup_tape_drive(config)
    lto_verify_util.verify_tape(config, tape_id)
    lto_util.move_virtual_tape_dir(config, tape_id, 'written', 'verified')
    lto_util.delete_dir_content(lto_util.get_tape_verify_dir(config))
    
    
if __name__ == "__main__":
    main()  