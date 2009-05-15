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

def get_media_ids(config, session_ids, domain):
    list = []
    for s in session_ids:
        if ltoTarUtil.db_session_id_exists(config, s):
            media_ids_qry = '/session[@id="'+s+'"]//'+domain+'/xs:string(@id)'
            xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_transcript_url(config)+'/data', media_ids_qry)
            list.extend(ltoUtil.get_parsed_xquery_value(xquery_result))
        else:
            print s+' is not a recognised session id.'
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)     
    return list

def check_media_ids_exist(config, items, domain):
    for i in items:
        if not lto_db_media_id_exists(domain, i, config):
            print 'There does not exist a '+domain+' file with the id '+i+' in the tape index files.'
            print 'Maybe the tar archive containing it is yet to be written to tape.' 
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
        md5_qry = 'string(//'+domain+'[@id="'+id+'"]/@md5)'
        
        tape_db = ltoUtil.get_lto_url(config)+'/data'
        tape_id = ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, tape_id_qry))[0]
        tar_block = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, tar_block_qry))[0])
        record_offset = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, record_offset_qry))[0])
        filename = ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, filename_qry))[0]
        filesize = int(ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, filesize_qry))[0])
        md5 = ltoUtil.get_parsed_xquery_value(ltoUtil.exec_url_xquery(config, tape_db, md5_qry))[0]
        block_offset = int(record_offset*512/bs)
        seek_block = tar_block + block_offset
        
        v = [tape_id, seek_block, filesize, record_offset, filename, md5]
        vectors.append(v)
        vectors.sort()
    return vectors

def check_total_size(config, vectors):
    total_size = 0
    for v in vectors:
        total_size += v[2]
    free_bytes = ltoUtil.get_freespace(ltoUtil.get_restore_dir(config))
    if total_size > free_bytes - (1024*1024):
        print 'Insufficient free space on drive ('+ltoUtil.format_bytes_to_gbs(free_bytes)+') to restore all files ('+ltoUtil.format_bytes_to_gbs(total_size)+').'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)

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
        filesize = v[2]
        record_offset = v[3]
        filename = v[4]
        md5 = v[5]
        
        blocks = int(filesize/bs)+2
        trim = (record_offset*512)%bs
        
        if not prev_tape_id == tape_id:
            raw_input('Insert tape: '+tape_id+' [Press Enter to continue]')
            if not setup_done:
                ltoWriteUtil.setup_tape_drive(config)
                setup_done = True
    
        print '\nSeeking to tape block: '+str(offset)
        p = subprocess.Popen('mt -f '+tape+' seek '+str(offset), shell=True)
        sts = os.waitpid(p.pid, 0)
    
        print 'Restoring file: '+filename
        p = subprocess.Popen('dd if='+tape+' bs='+str(bs)+' count='+str(blocks)+' | dd bs='+str(trim)+' skip=1 | tar -x -C '+restore_dir+' '+filename+' --occurrence', shell=True, stderr=subprocess.PIPE)
        sts = os.waitpid(p.pid, 0)
        
        #md5 check restored files
        if md5 == ltoUtil.get_md5_hash(restore_dir+'/'+filename):
            print 'Verified MD5: '+filename
        else: 
            print 'MD5 verification failed for '+filename
        
        prev_tape_id = tape_id

    print '\nAll files successfully restored to '+ltoUtil.get_restore_dir(config)
