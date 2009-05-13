
import sys
import os
import subprocess
import xml.dom.minidom
import shutil
import ltoUtil

def verify_tape(config, tape_id):
    print '\nVerifying index'
    bs = int(config.get('Tape', 'block_size_bytes'))
    tape = config.get('Tape', 'device')
    blocking_factor = bs/512
    written_dir = ltoUtil.get_tape_written_dir(config)+'/'+tape_id
    temp_dir = ltoUtil.get_temp_dir(config)
    original_dir = temp_dir+'/verify-tape/'+tape_id+'/original'
    archived_dir = temp_dir+'/verify-tape/'+tape_id+'/archived'
    ltoUtil.create_dir(original_dir)
    ltoUtil.create_dir(archived_dir)
    tape_xml_file = tape_id+'.xml'
    #Extract index file from tape
    p = subprocess.Popen('tar -x -b '+str(blocking_factor)+' -C '+archived_dir+' -f '+tape+' '+tape_xml_file, shell=True)
    sts = os.waitpid(p.pid, 0)
    #Unpack index file from disk archive
    index_tar_path = written_dir+'/'+tape_xml_file+'.tar'
    if not os.path.exists(index_tar_path):
        print 'Verification Error: The tar file '+index_tar_path+' does not exist.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    p = subprocess.Popen('tar -x -b '+str(blocking_factor)+' -C '+original_dir+' -f '+written_dir+'/'+tape_xml_file+'.tar ', shell=True)
    sts = os.waitpid(p.pid, 0)
    #Compare index files
    original_index = original_dir+'/'+tape_xml_file
    archived_index = archived_dir+'/'+tape_xml_file
    
    if not os.path.exists(archived_index):
        print 'Unable to restore tape index file '+tape_xml_file+' from tape. Please check the correct tape is in the drive.' 
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if not os.path.exists(original_index):
        print 'Unable to extract tape index file '+tape_xml_file+' from '+written_dir+'/'+tape_xml_file+'.tar.' 
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if not ltoUtil.compare(original_index, archived_index):
        print '\nIndex file verification failed.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    print 'OK'
    print '\nVerifying tape\n'
    position = 2
    #Parse index file into memory
    tape_xml_doc = xml.dom.minidom.parse(archived_index)
    tar_elems = tape_xml_doc.getElementsByTagName('tar')
    if len(tar_elems) == 0:
        print 'XML Error: The tape index file '+archived_index+' has no "tar" elements.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
        
    #Loop thru all tars on tape
    disk_tarfiles_verified = [tape_xml_file+'.tar']
    while True:
        p = subprocess.Popen('mt -f '+tape+' fsf 1', shell=True)
        sts = os.waitpid(p.pid, 0)
        tapedump_dir = archived_dir+'/'+str(position)
        diskdump_dir = original_dir+'/'+str(position)
        ltoUtil.create_dir(tapedump_dir)
        ltoUtil.create_dir(diskdump_dir)
        session_id = ""
        device_code = ""
        #Extract tarfile members from tape
        print 'Extracting tar archive #'+str(position)+' from tape'
        p = subprocess.Popen('tar -x -b '+str(blocking_factor)+' -C '+tapedump_dir+' -f '+tape, shell=True, stderr=subprocess.PIPE)
        stderr_value = p.stderr.read()
        sts = os.waitpid(p.pid, 0)
        if stderr_value == 'tar: This does not look like a tar archive\ntar: Error exit delayed from previous errors\n':
            print 'End of Data reached on tape'
            break
        t = tar_elems[position - 2]
        if int(t.getAttribute('position')) == position:
            session_id = t.getAttribute('sessionId')
            device_code = t.getAttribute('deviceCode')
            tar_name = session_id+'-'+device_code+'.tar'
            tarfile_path = written_dir+'/'+tar_name
            if not os.path.exists(tarfile_path):
                print 'Verification Error: The tar file '+tarfile_path+' does not exist.'
                print ltoUtil.get_script_name()+' script terminated.'
                sys.exit(2)
            #Unpack corresponding tarfile on disk
            print 'Extracting corresponding local tar archive '+tarfile_path+'\n'
            p = subprocess.Popen('tar -x -b '+str(blocking_factor)+' -C '+diskdump_dir+' -f '+written_dir+'/'+tar_name, shell=True)
            sts = os.waitpid(p.pid, 0)
            #Compare the extracted files with each other (byte for byte), and ensure that index file is correct
            tar_members = []
            for file in os.listdir(diskdump_dir):
                fp1 = os.path.join(diskdump_dir, file)
                fp2 = os.path.join(tapedump_dir, file)
                if not os.path.exists(fp2):
                    print '\nVerification Error: The file '+file+' was found on the local tape archive '+tarfile_path+', but not on the tape.'
                    print ltoUtil.get_script_name()+' script terminated.'
                    sys.exit(2)
                md5 = ltoUtil.compare(fp1, fp2)
                if not md5:
                    print '\nVerification Error: The file '+file+' failed the byte comparison with the local copy.'
                    print ltoUtil.get_script_name()+' script terminated.'
                    sys.exit(2)
                else:
                    print file+' byte comparison with local copy successful'
                    ref_file = session_id+'-'+device_code+'-referenced-items.xml'
                    if not file == ref_file:
                        #Verify each file against index file
                        children = t.childNodes
                        for c in children:
                            if c.nodeType == c.ELEMENT_NODE and c.getAttribute('filename') == file:
                                if md5 == c.getAttribute('md5'):
                                    print file+' MD5 check successful'
                                else: 
                                    print '\nVerification Error: The file '+file+' failed the md5 verification against the index file.'
                                    print ltoUtil.get_script_name()+' script terminated.'
                                    sys.exit(2)
                            grandchildren = c.childNodes
                            for g in grandchildren:
                                if g.nodeType == g.ELEMENT_NODE and g.getAttribute('filename') == file: 
                                    if md5 == g.getAttribute('md5'):
                                        print file+' MD5 check successful'
                                    else: 
                                        print '\nVerification Error: The file '+file+' failed the md5 verification against the index file.'
                                        print ltoUtil.get_script_name()+' script terminated.'
                                        sys.exit(2)
                tar_members.append(file)
            #Check that there are no unmatched tar members on the tape
            for m in os.listdir(tapedump_dir):
                if not m in tar_members:
                    print '\nVerification Error: The file '+m+' was found on the tape, but not on the corresponding local tape archive '+tarfile_path 
                    print ltoUtil.get_script_name()+' script terminated.'
                    sys.exit(2)
                
            disk_tarfiles_verified.append(tar_name)
        else:
            print 'Index File Error: Index file archives incorrectly ordered.'
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
        #Delete temporary files
        print '\n'
        shutil.rmtree(original_dir)
        shutil.rmtree(archived_dir)
        
        position += 1
        
    #Check that there are no unmatched tarfiles on the disk
    for f in os.listdir(written_dir):
        if f.endswith('.tar') and not f in disk_tarfiles_verified:
            print 'Verification Error: The tar archive '+written_dir+'/'+f+' was not found on the tape.'
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
    
    print 'Rewinding tape.'
    p = subprocess.Popen('mt -f '+tape+' rewind', shell=True, stderr=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)
    ltoUtil.terminate_on_error(p.stderr.read())        
    print '\nTape successfully verified.'
    
                
    
         
                        
                
                
        

        
        