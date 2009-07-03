#!/usr/bin/python

import optparse
import sys
import os
import xml.dom.minidom
import ConfigParser 
import ltoUtil
import ltoWriteUtil

def main():
    
    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-v", "--verify", dest="verify", action="store-true", help="Verify tape after writing")
    (options, args) = parser.parse_args()
    verify = options.verify
    ltoWriteUtil.check_write_args(args)
    tape_id = args[0]
    
    config = ConfigParser.ConfigParser()
    ltoUtil.load_config(config)
    ltoUtil.config_checks(config)
    ltoUtil.path_check(ltoUtil.get_tape_pending_dir(config)+'/'+tape_id)
    ltoWriteUtil.verify_virtual_tape(config, tape_id)
    
    ltoWriteUtil.setup_tape_drive(config)
    ltoWriteUtil.write_tape(config, tape_id)
    ltoUtil.move_virtual_tape_dir(config, tape_id, 'pending', 'written')
    
    
if __name__ == "__main__":
    main()  
        
        
        