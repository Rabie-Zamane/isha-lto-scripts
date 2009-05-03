'''
Created on 15-Apr-2009

@author: kevala
'''
import ConfigParser
import lto_util
import lto_tape_util
        

def main():
    
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    
    lto_util.config_checks(config)
    lto_util.path_check(lto_util.get_tape_build_dir(config))
    lto_util.path_check(lto_util.get_tape_pending_dir(config))
    lto_tape_util.check_tape_build_dir_contents(lto_util.get_tape_build_dir(config))
    lto_tape_util.check_tape_build_size(config)

    tape_xml_doc = lto_tape_util.create_tape_xml_doc(lto_util.get_curr_datetime(), config) 
    lto_tape_util.create_tape_index(tape_xml_doc, config)
    tape_id = lto_tape_util.db_import_tape_xml(config, tape_xml_doc)
        
    lto_tape_util.update_tape_xml(tape_xml_doc, tape_id)
    lto_tape_util.write_tape_xml_file(config, tape_xml_doc, tape_id)
    lto_tape_util.move_virtual_tape_files(config, tape_id)
    lto_util.delete_dir_content(lto_util.get_tape_build_dir(config))


if __name__ == "__main__":
    main()