#!/usr/local/bin/python2.6

import getpass
import optparse
import ConfigParser 
import ltoUtil
import ltoTarUtil

def main():

    parser = optparse.OptionParser(version="%prog 1.0")
    (options, args) = parser.parse_args()
    ltoTarUtil.check_tar_args(args)
    session_id = args[0]
    device_code = args[1]
    path = args[2]
    username = args[3]
    password = args[4]

    config = ConfigParser.ConfigParser()
    ltoUtil.load_config(config)
    ltoUtil.authenticate(config, username, password)
    ltoUtil.config_checks(config)
    category = ltoTarUtil.get_media_category(config, path)
    ltoUtil.path_check(path) 
    ltoTarUtil.media_file_types_check(config, category, path)
    
    ltoUtil.path_check(ltoUtil.get_tar_build_dir(config))
    ltoUtil.path_check(ltoUtil.get_proxy_dir(config))
    ltoTarUtil.session_device_check(config, session_id, device_code)
    ltoUtil.delete_dir_content(ltoUtil.get_tar_build_dir(config))
    
    ltoTarUtil.create_referenced_items_file(config, session_id, device_code) 
    db_media_xml_doc = ltoTarUtil.create_db_session_media_xml(session_id, device_code)
    tar_xml_doc = ltoTarUtil.create_tar_xml_doc(session_id, device_code)
    
    ltoTarUtil.main_loop('video', category, config, session_id, path, db_media_xml_doc, tar_xml_doc)
    ltoTarUtil.main_loop('audio', category, config, session_id, path, db_media_xml_doc, tar_xml_doc)
    ltoTarUtil.main_loop('image', category, config, session_id, path, db_media_xml_doc, tar_xml_doc)
        
    ltoTarUtil.create_tar_archive(config, session_id, device_code, tar_xml_doc)
    ltoTarUtil.create_tar_xml_file(config, session_id, device_code, tar_xml_doc)

    ltoTarUtil.write_media_xml_to_db(config, session_id, device_code, db_media_xml_doc, username, password)
    ltoTarUtil.move_tar_files(config, session_id, device_code)

    ltoTarUtil.generate_proxy_files(config, 'video')
    ltoTarUtil.generate_proxy_files(config, 'audio')
    ltoTarUtil.generate_proxy_files(config, 'image')

    ltoUtil.delete_dir_content(ltoUtil.get_tar_build_dir(config))
    

if __name__ == "__main__":
    main()

             
   
