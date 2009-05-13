#!/usr/bin/python

import optparse
import sys
import os
import xml.dom.minidom
import ConfigParser 
import ltoUtil
import ltoWriteUtil
import ltoVerifyUtil


def main():

    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-i", "--tape-id", dest="tape_id", type="string", help="Specify tape id")
    (options, args) = parser.parse_args()
    
    ltoWriteUtil.check_write_args(args)
    tape_id = args[0]
    
    config = ConfigParser.ConfigParser()
    config.read('/home/kevala/workspace/ishaLto/src/lto.cfg')
    
    ltoUtil.config_checks(config)
    ltoUtil.path_check(ltoUtil.get_tape_written_dir(config)+'/'+tape_id)
    ltoUtil.delete_dir_content(ltoUtil.get_tape_verify_dir(config))
    
    ltoWriteUtil.setup_tape_drive(config)
    ltoVerifyUtil.verify_tape(config, tape_id)
    ltoUtil.move_virtual_tape_dir(config, tape_id, 'written', 'verified')
    ltoUtil.delete_dir_content(ltoUtil.get_tape_verify_dir(config))
    
    
if __name__ == "__main__":
    main()  