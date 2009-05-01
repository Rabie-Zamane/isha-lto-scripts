'''
Created on 12-Apr-2009

@author: kevala
'''
#!/usr/bin/python

import os
import sys
import getpass
import getopt
import string
import subprocess
import ConfigParser 
import lto_util


def media_process_loop(domain, config, session_id, path, db_media_xml_doc, tar_xml_doc): 
    
        previous_id = None
        for dirpath, dirnames, filenames in os.walk(path):
            for file in filenames:
                if lto_util.media_in_type(file, domain, config):
                    
                    filepath = os.path.join(dirpath, file)
                    media_id = lto_util.get_new_media_id(session_id, domain, config, previous_id)
                    db_media_xml_element = lto_util.generate_db_media_xml_element(filepath, domain, media_id)
                    lto_util.append_db_media_xml_element(db_media_xml_doc, db_media_xml_element)
                    
                    new_filepath = lto_util.get_tar_build_dir(config)+'/'+domain+'-'+media_id+'.'+string.lower(filepath[-3:])
                    lto_util.copy_media_file(filepath, new_filepath)
                    
                    lto_util.generate_par2_tar(config, new_filepath)
                    proxy_media_dir = config.get('Main', 'proxy_media_dir')
                    #lto_util.generate_low_res(domain, new_filepath, proxy_media_dir)
                    lto_util.append_tar_media_xml_element(tar_xml_doc, new_filepath, domain, media_id)
                    previous_id = media_id
                    
                    
def create_tar_archive(config, session_id, device_code, tar_xml_doc):
    
    tar_name = session_id+'-'+device_code+'.tar'
    tar_path = lto_util.get_tar_build_dir(config)+'/'+tar_name
    filelist = []
    for file in os.listdir(lto_util.get_tar_build_dir(config)):
        filelist.append(file)
    filelist.remove('referenced-items.xml')
    filelist.sort()   
    
    filelist_str = 'referenced-items.xml '+string.join(filelist, ' ')
    print 'Creating tar archive: '+tar_path
    p = subprocess.Popen('tar -cvR --format='+lto_util.get_tar_format(config)+' -C '+lto_util.get_tar_build_dir(config)+' -f '+tar_path+' '+filelist_str, shell=True, stdout=subprocess.PIPE)
    stdout_value = p.stdout.readlines()
    del stdout_value[0]
    for line in stdout_value:
        lto_util.update_block_xml_attributes(tar_xml_doc, line, config)
       
    lto_util.update_tar_xml_root_attributes(config, tar_xml_doc, tar_name)
    
    
def create_tar_xml_file(config, session_id, device_code, tar_xml_doc):
    
    xmlfile = open(lto_util.get_tar_build_dir(config)+'/'+session_id+'-'+device_code+'.xml', "w")
    pretty_doc = tar_xml_doc.toprettyxml()
    #Hack to put id attribute at the start
    pretty_doc = string.replace(pretty_doc, '_id="', 'id="')
    xmlfile.write(pretty_doc)
    xmlfile.close()
    
    
def write_media_xml_to_db(config, session_id, device_code, db_media_xml_doc):
    
    #Ask user for confirmation to write media xml to database
    update = raw_input('Update database with session-media metadata? [y/n]: ')
    xml_media_filename = session_id+'-'+device_code+'-media.xml'
    xml_media_filepath = lto_util.get_tar_build_dir(config)+'/'+xml_media_filename
    if update == 'y':
        username = raw_input('username: ')
        password = getpass.getpass('password: ')
        if lto_util.db_add_media_xml(config, db_media_xml_doc, username, password):
            print 'Database updated'
        else:
            print 'Failed to update database'
            lto_util.write_xml(db_media_xml_doc, xml_media_filepath)
            print 'Media xml saved to '+xml_media_filepath
    else:
        lto_util.write_xml(db_media_xml_doc, lto_util.get_tar_build_dir(config)+'/'+xml_media_filename)
        print 'Media xml saved to '+xml_media_filepath
       

def main():
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:d:p:", ["session=", "device=", "path="])
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2) 
 
    for opt, arg in opts:                
        if opt in ('-s', '--session'):      
            session_id = arg                                  
        elif opt in ( '-d', '--device'):                
            device_code = arg                             
        elif opt in ('-p', '--path'): 
            path = arg               
            
    lto_util.argument_checks(session_id, device_code, path)
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    lto_util.config_checks(config)
    #lto_util.db_session_id_exists(session_id)
    
    #Create XML structures
    lto_util.create_referenced_items_file('referenced-items.xml', config, session_id) 
    db_media_xml_doc = lto_util.create_db_session_media_xml(session_id, device_code)
    tar_xml_doc = lto_util.create_tar_xml_doc(session_id, device_code)
    
    media_process_loop('video', config, session_id, path, db_media_xml_doc, tar_xml_doc)
    media_process_loop('audio', config, session_id, path, db_media_xml_doc, tar_xml_doc)
    media_process_loop('image', config, session_id, path, db_media_xml_doc, tar_xml_doc)

    create_tar_archive(config, session_id, device_code, tar_xml_doc)
    create_tar_xml_file(config, session_id, device_code, tar_xml_doc)

    write_media_xml_to_db(config, session_id, device_code, db_media_xml_doc)
    

if __name__ == "__main__":
    main()


#===============================================================================
#    if len(media_filepaths) == 0:
#        print 'No media files were found in '+path+'. create-archive script terminated'
#        sys.exit(2)
#===============================================================================
        
    #Clean work folder
             
   