#!/usr/bin/python

import ConfigParser
import ltoUtil
import ltoBuildUtil
        
def main():
    
    config = ConfigParser.ConfigParser()
    ltoUtil.load_config(config)
    ltoUtil.config_checks(config)
    ltoUtil.path_check(ltoUtil.get_tape_build_dir(config))
    ltoUtil.path_check(ltoUtil.get_tape_pending_dir(config))
    ltoBuildUtil.check_tape_build_dir_contents(ltoUtil.get_tape_build_dir(config))
    ltoBuildUtil.check_tape_build_size(config)

    tape_xml_doc = ltoBuildUtil.create_tape_xml_doc(ltoUtil.get_curr_datetime(), config) 
    ltoBuildUtil.create_tape_index(tape_xml_doc, config)
    tape_id = ltoBuildUtil.db_import_tape_xml(config, tape_xml_doc)
        
    ltoBuildUtil.update_tape_xml(tape_xml_doc, tape_id)
    ltoBuildUtil.write_tape_xml_file(config, tape_xml_doc, tape_id)
    ltoBuildUtil.move_build_virtual_tape_files(config, tape_id)
    ltoUtil.delete_dir_content(ltoUtil.get_tape_build_dir(config))


if __name__ == "__main__":
    main()