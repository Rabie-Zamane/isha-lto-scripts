'''
Created on 04-May-2009

@author: kevala
'''

import os
import sys
import xml.dom.minidom
import subprocess
import time
import string
import lto_util


def check_write_args(options):
    if options.tape_id == None or options.tape_id =="":
        print 'Argument Error: tape id not specified. '+lto_util.get_script_name()+' script terminated.'
        sys.exit(2)
        
def verify_virtual_tape(config, tape_id):
    #Parse tape xml file and verify the existence and md5 hashes for each tar file
    print 'Verifying virtual tape: '+tape_id
    if tape_id:
        tape_xml_path = lto_util.get_tape_pending_dir(config)+'/'+tape_id+'/'+tape_id+'.xml'
    else:
        print 'Internal Error: tape_id variable not set.'
        print  sys._getframe().f_code
        print lto_util.get_script_name()+' script terminated.'
        sys.exit(2)
    if not os.path.exists(tape_xml_path):
        print 'IO Error: The tape index file '+tape_xml_path+' does not exist.'
        print lto_util.get_script_name()+' script terminated.'
        sys.exit(2)
        
    tape_xml_doc = xml.dom.minidom.parse(tape_xml_path)
    tar_elems = tape_xml_doc.getElementsByTagName('tar')
    if len(tar_elems) == 0:
        print 'XML Error: The tape index file '+tape_xml_path+' has no "tar" elements.'
        print lto_util.get_script_name()+' script terminated.'
        sys.exit(2)
        
    for tar_elem in tar_elems:
        session_id = tar_elem.getAttribute('sessionId')
        device_code = tar_elem.getAttribute('deviceCode')
        tarfile_name = session_id+'-'+device_code+'.tar'
        tarfile_path = lto_util.get_tape_pending_dir(config)+'/'+tape_id+'/'+tarfile_name
        if not os.path.exists(tarfile_path):
            print 'Verification Error: The tar file '+tarfile_path+', specified in the tape index, does not exist.'
            print lto_util.get_script_name()+' script terminated.'
            sys.exit(2)
            
        stored_tar_md5 = tar_elem.getAttribute('md5')
        if not stored_tar_md5 == lto_util.get_md5_hash(tarfile_path):
            print 'Verification Error: MD5 mismatch for tar file '+tarfile_path
            print lto_util.get_script_name()+' script terminated.'
            sys.exit(2)
    print 'OK\n'
    
def setup_tape_drive(config):
    bs = config.get('Tape', 'block_size_bytes')
    tape = config.get('Tape', 'device')
    #if not os.path.exists(tape):
    #   print 'Tape device '+tape+' is not available.'
    #  print lto_util.get_script_name()+' script terminated.'
    # sys.exit(2)
    #Getting Drive status
    print 'Checking drive status\n'
    
    while 1:
        p = subprocess.Popen('mt -f '+tape+' status', shell=True, stdout=subprocess.PIPE)
        stdout_value = p.stdout.read()
        sts = os.waitpid(p.pid, 0)
        if not 'ONLINE' in stdout_value:
            raw_input('Tape drive not ready. (Check drive is switched on and a tape is inserted). [Press Enter to continue]')
            time.sleep(7)
        else:
            break
        
    print string.strip(stdout_value)
    print 'OK'
    print 'Checking tape drive options'
    p = subprocess.Popen('mt -f '+tape+' stshowopt', shell=True, stdout=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)
    if not 'scsi2logical' in p.stdout.read():
        print 'The st "scsi2logical" option must be set. This can be specified in /etc/stinit.def'
        print lto_util.get_script_name()+' script terminated.'
        sys.exit(2)
    print 'OK'
    print 'Setting tape drive block size to ' +str(bs)+ ' bytes'
    p = subprocess.Popen('mt -f '+tape+' setblk '+str(bs), shell=True, stderr=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)
    lto_util.terminate_on_error(p.stderr.read())
    print 'Rewinding tape'
    p = subprocess.Popen('mt -f '+tape+' rewind', shell=True, stderr=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)
    lto_util.terminate_on_error(p.stderr.read())
        
def write_tape(config, tape_id):
    print '\nWriting tape'
    bs = int(config.get('Tape', 'block_size_bytes'))
    tape = config.get('Tape', 'device')
    blocking_factor = bs/512
    tape_index_size = int(config.get('Tape', 'index_size_mb'))*1024*1024
    tape_xml_path = lto_util.get_tape_pending_dir(config)+'/'+tape_id
    tape_xml_file = tape_id+'.xml'
    tape_xml_tarfile_path = tape_xml_path+'/'+tape_xml_file+'.tar'
    print 'Writing '+tape_id+'.xml index file at position 1 (block number 0)'
    #First create index tar file
    p = subprocess.Popen('tar -c -b '+str(blocking_factor)+' --format='+lto_util.get_tar_format(config)+' -C '+tape_xml_path+' -f '+tape_xml_tarfile_path+' '+tape_xml_file, shell=True)
    sts = os.waitpid(p.pid, 0)
    #Next use dd to pad the index tar file with null bytes so that it becomes the size given by tape_index_size
    index_tar_size = lto_util.get_filesize(tape_xml_tarfile_path)
    null_size = tape_index_size - index_tar_size
    p = subprocess.Popen('dd if=/dev/zero of='+tape_xml_tarfile_path+' bs='+str(null_size)+' count=1 oflag=append conv=notrunc status=noxfer', shell=True)
    sts = os.waitpid(p.pid, 0)
    #Finally, use dd to write it to tape
    p = subprocess.Popen('dd if='+tape_xml_tarfile_path+' of='+tape+' bs='+str(bs), shell=True)
    sts = os.waitpid(p.pid, 0)
    index_doc = xml.dom.minidom.parse(tape_xml_path+'/'+tape_xml_file)
    tar_elems = index_doc.getElementsByTagName('tar')
    for index, tar in enumerate(tar_elems): 
        session_id = tar.getAttribute('sessionId')
        device_code = tar.getAttribute('deviceCode')
        position = int(tar.getAttribute('position'))
        stored_block = int(tar.getAttribute('block'))
        tar_id = session_id+'-'+device_code
        if position != index+2:
            print 'Archives incorrectly ordered in '+tape_id+'.xml file.'
            print lto_util.get_script_name()+' script terminated.'
            sys.exit(2)
        
        tar_path = lto_util.get_tape_pending_dir(config)+'/'+tape_id+'/'+tar_id+'.tar'
        p = subprocess.Popen('mt -f '+tape+' tell', shell=True, stdout=subprocess.PIPE)
        stdout_value = p.stdout.read()
        block_number = int(stdout_value[stdout_value.rfind(' ')+1:-2])
        sts = os.waitpid(p.pid, 0)
        if not block_number == stored_block:
            print 'Error: Calculated block offset ('+str(stored_block)+') not matching actual block offset ('+block_number+') for file: '+  tar_id+'.tar'
            print lto_util.get_script_name()+' script terminated.'
            sys.exit(2)
        print 'Writing '+tar_id+'.tar file at position '+str(index+2)+' (block number '+str(block_number)+')'
        p = subprocess.Popen('dd if='+tar_path+' of='+tape+' bs='+str(bs), shell=True)
        sts = os.waitpid(p.pid, 0)
    p = subprocess.Popen('mt -f '+tape+' rewind', shell=True)
    print 'Rewinding tape'
    sts = os.waitpid(p.pid, 0)
    print 'Tape writing completed\nOK'
    
