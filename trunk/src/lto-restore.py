
import optparse
import ConfigParser
import subprocess
import os
import ltoUtil
import ltoWriteUtil
import ltoRestoreUtil

def main():

    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-m", "--media-type", dest="media_type", type="string", help="Specify media type (video/audio/image). Default is video")
    parser.add_option("-s", "--session", dest="use_session_ids", action="store_true", help="Arguments must be session ids. (All media for each session will be restored)")
    parser.add_option("-f", "--file", dest="use_files", action="store_true", help="Arguments must be files. (All media listed in each file will be restored)")
    (options, args) = parser.parse_args()
    
    ltoRestoreUtil.check_restore_args(options, args)
    if options.media_type == None or options.media_type == "":
        domain = 'video' 
    else:
        domain = options.media_type
    items = args

    config = ConfigParser.ConfigParser()
    ltoUtil.load_config(config)
    ltoUtil.config_checks(config)
    ltoUtil.path_check(ltoUtil.get_restore_dir(config))

    if options.use_files:
        items = ltoRestoreUtil.parse_files(args)
        
    if options.use_session_ids:
        items = ltoRestoreUtil.get_media_ids(config, args, domain)
    
    ltoRestoreUtil.check_media_ids_exist(config, items, domain)
    item_vectors = ltoRestoreUtil.get_item_vectors(config, items, domain)
    ltoRestoreUtil.check_total_size(config, item_vectors)
    ltoRestoreUtil.restore_media_items(config, domain, item_vectors)
    
    
if __name__ == "__main__":
    main()

