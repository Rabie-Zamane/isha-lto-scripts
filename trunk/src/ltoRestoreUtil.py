import sys
import os
import subprocess
import ltoUtil
import ltoTarUtil
import ltoWriteUtil

def check_restore_args(opts, args):
    if len(args) == 0:
        print 'Missing arguments.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if opts.use_session_ids == True and opts.use_files == True:
        print 'You cannot specify both the -s and -f options simultaneously.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if not (opts.media_type == None or opts.media_type == 'video' or opts.media_type == 'audio' or opts.media_type == 'image'):
        print 'Invalid media type: "'+opts.media_type+'".'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    
def parse_files(args):
    ids = []
    for f in args:
        if not os.path.exists(f):
            print 'Cannot find file '+f
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
        fh = open(f, 'r')
        for line in fh.readlines():
            if not (line.strip() == None or line.strip() == ""):
                ids.append(line.strip())
    return ids

def get_media_ids(config, session_id, domain):
    media_ids_qry = '/session[@id="'+session_id+'"]//'+domain+'/xs:string(@id)'
    xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_transcript_url(config)+'/data', media_ids_qry)
    return ltoUtil.get_parsed_xquery_value(xquery_result)

def check_media_ids_exist(config, items, domain):
    for i in items:
        if not lto_db_media_id_exists(domain, i, config):
            print 'There does not exist a '+domain+' file with the id '+i+' in the tape index files.'
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)

def lto_db_media_id_exists(domain, id, config):
    media_id_exists_for_domain_qry = 'exists(/tape/tar/'+domain+'[@id="'+id+'"])'
    xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_lto_url(config)+'/data', media_id_exists_for_domain_qry)
    if ltoUtil.get_parsed_xquery_value(xquery_result) == ['true']:
        return True
    else:
        return False

def get_item_vectors(config, items, domain):
    bs = int(ltoUtil.get_blocksize(config))
    vectors = []
    for id in items:
        tape_id_qry = 'string(//'+domain+'[@id="'+id+'"]/../../@id)'
        tar_block_qry = 'string(//'+domain+'[@id="'+id+'"]/../@block)'
        record_offset_qry = 'string(//'+domain+'[@id="'+id+'"]/@recordOffset)'
        filename_qry = 'string(//'+domain+'[@id="'+id+'"]/@filename)'
        filesize_qry = 'string(//'+domain+'[@id="'+id+'"]/@size)'
        
        tape_db = ltoUtil.get_lto_url(config)+'/data'
        tape_id = ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, tape_id_qry))[0]
        tar_block = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, tar_block_qry))[0])
        record_offset = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, record_offset_qry))[0])
        filename = ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, filename_qry))[0]
        filesize = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, filesize_qry))[0])
        block_offset = int(record_offset*512/bs)
        seek_block = tar_block + block_offset
        num_blocks = int(filesize/bs)+2
        trim_bytes = (record_offset*512)%bs
        
        v = [tape_id, seek_block, num_blocks, trim_bytes, filename]
        vectors.append(v)
        vectors.sort()
    return vectors

def restore_media_items(config, domain, vectors):
    tape = ltoUtil.get_tape_device(config)
    restore_dir = ltoUtil.get_restore_dir(config)
    bs = int(ltoUtil.get_blocksize(config))
    blocking_factor = bs/512
    setup_done = False
    prev_tape_id = ""
    
    for v in vectors:
        tape_id = v[0]
        offset = v[1]
        blocks = v[2]
        trim = v[3]
        filename = v[4]
        
        if not prev_tape_id == tape_id:
            raw_input('Insert tape: '+tape_id+' [Press Enter to continue]')
            if not setup_done:
                ltoWriteUtil.setup_tape_drive(config)
                setup_done = True
    
        print '\nSeeking to tape block: '+str(offset)
        p = subprocess.Popen('mt -f '+tape+' seek '+str(offset), shell=True)
        sts = os.waitpid(p.pid, 0)
    
        print '\nRestoring file: '+filename

        p = subprocess.Popen('dd if='+tape+' bs='+str(bs)+' count='+str(blocks)+' of='+restore_dir+'/'+filename+'.dd', shell=True)
        sts = os.waitpid(p.pid, 0)
        p = subprocess.Popen('dd if='+restore_dir+'/'+filename+'.dd bs='+str(trim)+' skip=1 | tar -xv -C '+restore_dir+' '+filename+' --occurrence', shell=True)
        sts = os.waitpid(p.pid, 0)
        
        #p = subprocess.Popen('tar -xv -b '+str(blocking_factor)+' --format='+ltoUtil.get_tar_format(config)+' -C '+ltoUtil.get_restore_dir(config)+' -f '+tape+' '+filename+' --occurrence', shell=True)
        
        prev_tape_id = tape_id

    print 'All files successfully restored to '+ltoUtil.get_restore_dir(config)
