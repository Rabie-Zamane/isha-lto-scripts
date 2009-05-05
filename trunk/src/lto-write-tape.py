'''
Created on 21-Apr-2009

@author: kevala
'''

import optparse
import sys
import os
import xml.dom.minidom
import ConfigParser 
import lto_util
import lto_write_util


def main():
    
    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-i", "--tape-id", dest="tape_id", type="string", help="Specify tape id")
    (options, args) = parser.parse_args()
    
    lto_write_util.check_write_args(options)
    tape_id = options.tape_id
    
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    
    lto_util.config_checks(config)
    lto_util.path_check(lto_util.get_tape_pending_dir(config)+'/'+tape_id)
    lto_write_util.verify_virtual_tape(config, tape_id)
    
    lto_write_util.setup_tape_drive(config)
    lto_write_util.write_tape(config, tape_id)
    lto_util.move_virtual_tape_dir(config, tape_id, 'pending', 'written')
    
    
if __name__ == "__main__":
    main()  
        
        
        