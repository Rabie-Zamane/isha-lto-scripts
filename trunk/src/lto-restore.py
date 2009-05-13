
import optparse
import ConfigParser
import subprocess
import os
import ltoUtil
import ltoWriteUtil

def main():

    parser = optparse.OptionParser(version="%prog 1.0")
    parser.add_option("-m", "--media-type", dest="media_type", type="string", help="Specify media type (video/audio/image)")
    parser.add_option("-i", "--id", dest="media_id", type="string", help="Specify media id")
    (options, args) = parser.parse_args()
    
    domain = options.media_type
    media_id = options.media_id
    
    config = ConfigParser.ConfigParser()
    config.read('lto.cfg')
    
    ltoUtil.config_checks(config)
    
    bs = int(ltoUtil.get_blocksize(config))
    blocking_factor = bs/512
    tar_block_qry = 'string(//'+domain+'[@id="'+media_id+'"]/../@block)'
    record_offset_qry = 'string(//'+domain+'[@id="'+media_id+'"]/@recordOffset)'
    tape_id_qry = 'string(//'+domain+'[@id="'+media_id+'"]/../../@id)'
    
    tape = ltoUtil.get_tape_device(config)
    tape_db = ltoUtil.get_lto_url(config)+'/data'
    tape_id = ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, tape_id_qry))
    tar_block = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, tar_block_qry)))
    record_offset = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, record_offset_qry)))
    
    block_offset = int(record_offset/512)
    seek_block = tar_block + block_offset
    
    raw_input('Insert tape: '+tape_id+' [Press Enter to continue]')
    
    ltoWriteUtil.setup_tape_drive(config)
    
    print '\nSeeking to tape block: '+str(seek_block)
    p = subprocess.Popen('mt -f '+tape+' seek '+str(seek_block), shell=True, stderr=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)
    ltoUtil.terminate_on_error(p.stderr.read())
    
    filename = domain+'-'+media_id
    print '\nRestoring file: '+filename
    p = subprocess.Popen('tar -xv -b '+str(blocking_factor)+' --format='+ltoUtil.get_tar_format(config)+' -C /lto-stage/restored -f'+tape+' '+filename+'.mp4 --occurrence', shell=True)
    sts = os.waitpid(p.pid, 0)
    
if __name__ == "__main__":
    main()

