'''
Created on 21-Apr-2009

@author: kevala
'''

import getopt
import sys
import subprocess
import os
import xml.dom.minidom


def check_tape_folder_exists(path):
        if os.access(path, os.F_OK):
            print 'Found '+path
        else:
            print 'Could not find '+path+' .write-tape script terminated'
            sys.exit(1)
            
def setup_tape_drive(tape_device, blocksize):
    bs_bytes = blocksize * 512
    p = subprocess.Popen('mt -f '+tape_device+' setblk '+str(bs_bytes), shell=True)
    print 'Setting tape drive block size to ' +str(bs_bytes)+ ' bytes'
    sts = os.waitpid(p.pid, 0)
    p = subprocess.Popen('mt -f '+tape_device+' drvbuffer 1', shell=True)
    print 'Activating tape drive buffer'
    sts = os.waitpid(p.pid, 0)
    p = subprocess.Popen('mt -f '+tape_device+' stoptions scsi2logical', shell=True)
    print 'Setting tape drive scsi2logical option'
    sts = os.waitpid(p.pid, 0)
    p = subprocess.Popen('mt -f '+tape_device+' rewind', shell=True)
    print 'Rewinding tape'
    sts = os.waitpid(p.pid, 0)

def write_tape(tape_home, tape_device, id, tape_index_size_bytes, bs_bytes):
    filepath = tape_home+'/pending/'+id+'/'+id+'.xml'
    print filepath
    print 'dd if='+filepath+' of='+tape_device+' bs='+str(tape_index_size_bytes)
    p = subprocess.Popen('dd if='+filepath+' of='+tape_device+' bs='+str(tape_index_size_bytes)+' -fill', shell=True)
    print 'Writing '+id+'.xml file at position 1'
    sts = os.waitpid(p.pid, 0)
    
    doc = xml.dom.minidom.parse(filepath)
    tarElems = doc.getElementsByTagName('tar')
    for index, tar in enumerate(tarElems): 
        session_id = tar.getAttribute('sessionId')
        device_code = tar.getAttribute('deviceCode')
        position = int(tar.getAttribute('position'))
        tar_id = session_id+'-'+device_code
        
        if position != index+2:
            print 'Archives incorrectly ordered in '+id+'.xml file. write-tape script terminated.'
            sys.exit(1)
        
        tar_path = tape_home+'/pending/'+id+'/'+tar_id+'.tar'
        p = subprocess.Popen('mt -f '+tape_device+' tell', shell=True, stdout=subprocess.PIPE)
        stdout_value = p.stdout.readlines()
        print 'Tape '+str(stdout_value[0])
        sts = os.waitpid(p.pid, 0)
        p = subprocess.Popen('dd if='+tar_path+' of='+tape_device+' bs='+str(bs_bytes), shell=True)
        print 'Writing '+tar_id+'.tar file at position '+str(index+2)
        sts = os.waitpid(p.pid, 0)
        
    print 'Tape writing completed'
    p = subprocess.Popen('mt -f '+tape_device+' rewind', shell=True)
    print 'Rewinding tape'
    sts = os.waitpid(p.pid, 0)
    
    


def main():
    
    lto_home = '/lto-stage'
    tape_home = lto_home+'/tapes'
    
    blocksize = 128
    blocksize_bytes = blocksize * 512
    tape_index_size_bytes = 100 * 1024 * 1024
    tape_device = '/dev/nst0'
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:", ["id="])
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2) 

    for opt, arg in opts:                
        if opt in ('-i', '--id'):      
            tape_id = arg                                  
        
    check_tape_folder_exists(tape_home+'/pending/'+tape_id)
    setup_tape_drive(tape_device, blocksize)
    write_tape(tape_home, tape_device, tape_id, tape_index_size_bytes, blocksize_bytes)
    
    
if __name__ == "__main__":
    main()  
        
        
        