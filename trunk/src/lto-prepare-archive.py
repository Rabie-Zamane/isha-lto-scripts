'''
Created on 12-Apr-2009

@author: kevala
'''
#!/usr/bin/python

import getpass
import optparse
import ConfigParser 
import lto_util
import lto_prepare_util

def main():

    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-s", "--session", dest="session_id", type="string", help="Specify session id")
    parser.add_option("-d", "--device", dest="device_code", type="string", help="Specify device code")
    parser.add_option("-p", "--path", dest="path", type="string", help="Specify path to media files")
    (options, args) = parser.parse_args()

    lto_prepare_util.check_archive_args(options)
    session_id = options.session_id
    device_code = options.device_code
    path = options.path
    
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    
    lto_util.config_checks(config)
    category = lto_prepare_util.get_media_category(config, path)
    lto_util.path_check(path) 
    lto_prepare_util.media_file_types_check(config, category, path)
    
    lto_util.path_check(lto_util.get_tar_build_dir(config))
    lto_util.path_check(lto_util.get_proxy_media_dir(config))
    lto_prepare_util.session_device_check(config, session_id, device_code)
    lto_util.delete_dir_content(lto_util.get_tar_build_dir(config))
    
    lto_prepare_util.create_referenced_items_file(config, session_id, device_code) 
    db_media_xml_doc = lto_prepare_util.create_db_session_media_xml(session_id, device_code)
    tar_xml_doc = lto_prepare_util.create_tar_xml_doc(session_id, device_code)
    
    lto_prepare_util.media_process_loop('video', category, config, session_id, path, db_media_xml_doc, tar_xml_doc)
    lto_prepare_util.media_process_loop('audio', category, config, session_id, path, db_media_xml_doc, tar_xml_doc)
        
    lto_prepare_util.create_tar_archive(config, session_id, device_code, tar_xml_doc)
    lto_prepare_util.create_tar_xml_file(config, session_id, device_code, tar_xml_doc)

    lto_prepare_util.write_media_xml_to_db(config, session_id, device_code, db_media_xml_doc)
    lto_prepare_util.move_tar_files(config, session_id, device_code)
    lto_util.delete_dir_content(lto_util.get_tar_build_dir(config))
    

if __name__ == "__main__":
    main()

             
   