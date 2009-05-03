'''
Created on 15-Apr-2009

@author: kevala
'''

import os
import sys
import xml.dom.minidom
import datetime
import urllib
import urllib2
import lto_util
import base64
import getpass
import ConfigParser
import lto_util
import lto_tape_util


def update_tape_xml(doc, id):
    tapeElement = doc.documentElement
    tapeElement.setAttribute('_id', id)
    return doc
        

def main():
    
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    
    lto_util.config_checks(config)
    lto_util.path_check(lto_util.get_tape_build_dir(config))
    lto_tape_util.check_tape_build_dir_contents(lto_util.get_tape_build_dir(config))
    lto_tape_util.check_tape_build_size(config)

    tape_xml_doc = lto_tape_util.create_tape_xml_doc(lto_util.get_curr_datetime(), config) 
    lto_tape_util.create_tape_index(tape_xml_doc, config)
    tape_id = lto_tape_util.db_import_tape_xml(config, tape_xml_doc)
        
    #Import tape.xml to the xml database
    username = raw_input('username: ')
    password = getpass.getpass('password: ')
    
    if tape_id:
        print 'database updated'
    else:
        print 'Failed to update database. create-virtual-tape script terminated'
        sys.exit(1)
    
    update_tape_xml(tapeXmlDoc, tape_id)
    tape_dir = tape_home+'/pending/'+tape_id
    os.mkdir(tape_dir)
    lto_util.write_xml(tapeXmlDoc, tape_dir+'/'+tape_id+'.xml')
    
         
         
if __name__ == "__main__":
    main()