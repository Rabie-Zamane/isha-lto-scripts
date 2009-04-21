'''
Created on 12-Apr-2009

@author: kevala
'''
#!/usr/bin/python

import distutils.file_util
import os
import sys
import getpass
import getopt
import string
import subprocess
import lto_util

def main():
    
    host = 'localhost:8080'
    
    lto_home = '/lto-stage'
    tar_home = lto_home+'/tars' 
    preview_home = lto_home+'/h261'
    
    blocksize = 128
    archivetype = 'pax'
    
    par2cmd = '/usr/bin/par2-multicpu/par2'
    par2redundancy = 5
    par2numfiles = 1
    par2memory = 1000
    
    
    mp4s = []
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:d:i:h", ["session=", "device=", "start-id=", "host"])
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2) 

    for opt, arg in opts:                
        if opt in ('-s', '--session'):      
            sessionid = arg                                  
        elif opt in ( '-d', '--device'):                
            deviceid = arg                             
        elif opt in ('-i', '--start-id'): 
            startId = arg               
        elif opt in ('-h', '--host'):
            host = arg
    
    lto_util.create_tar_event_metadata_file('referenced-items.xml', sessionid, host)
    mediasXmlDoc = lto_util.create_media_metadata_xml(sessionid, deviceid)
    tarXmlDoc = lto_util.create_tar_xml(sessionid, deviceid)
    firstmediaid = lto_util.db_get_next_media_id(sessionid, 'video')
    
    for dirpath, dirnames, filenames in os.walk(os.getcwd()):
        for file in filenames:
            if file.endswith('.MP4'):
                mp4s.append(os.path.join(dirpath, file))
                mp4s.sort()
                
    #Main loop
    for index, mp4 in enumerate(mp4s):
        
        rawxml = mp4[0:-4]+'M01.XML'
        if index < len(mp4s)-1:
            nextrawxml = mp4s[index+1][0:-4]+'M01.XML'
        else:
            nextrawxml = rawxml
            
        xfile = open(rawxml)
        timestamp = lto_util.get_timestamp(xfile)
        originalid = lto_util.get_originalid(rawxml)
        duration = lto_util.get_duration(xfile)
        autosplit = lto_util.get_autosplit(rawxml, nextrawxml)
        xfile.close()
         
        newmediaid = firstmediaid[:firstmediaid.find('-')]+'-'+str(int(firstmediaid[firstmediaid.find('-')+1:])+index)
        newfilename = 'video-'+newmediaid+'.mp4'
        distutils.file_util.copy_file(mp4, os.path.join(os.getcwd(), newfilename))
        lto_util.append_media_element(mediasXmlDoc, newmediaid, timestamp, duration, originalid, autosplit)
        
        lto_util.generate_par2_tar(par2cmd, par2redundancy, par2memory, par2numfiles, newfilename, blocksize, archivetype)
        distutils.file_util.copy_file(rawxml, os.getcwd())
        rawxmlname = rawxml[str(rawxml).rfind('/')+1:len(str(rawxml))]
        suppfiles = [rawxmlname]
        lto_util.generate_supp_tar(newfilename, suppfiles, blocksize, archivetype)
        lto_util.generate_preview(newfilename, preview_home)
        
        lto_util.generate_media_index_xml(tarXmlDoc, newfilename, 'video', newmediaid)
    
    #Create the main tar archive
    filelist = []
    tarname = sessionid+'-'+deviceid+'.tar'
    
    for file in os.listdir(os.getcwd()):
        if file.endswith('.mp4') or file.endswith('.tar'): 
            filelist.append(file)
            filelist.sort()      
            
    fileliststr = 'referenced-items.xml '+string.join(filelist, ' ')
    p = subprocess.Popen('star -c -v -b'+str(blocksize)+' artype='+archivetype+' -block-number f='+tarname+' -fifo fs=1g '+fileliststr, shell=True, stdout=subprocess.PIPE)
    stdout_value = p.stdout.readlines()
    for line in stdout_value:
        offset = line[5:line.find(':')].strip()
        filename = line[line.find(':')+4:line.find(' ',line.find(':')+4)]
        if filename != 'referenced-items.xml':
            lto_util.update_block_xml_attributes(tarXmlDoc, 'video', filename, offset)
        
    #Cleanup    
    os.remove('referenced-items.xml')
    for f in filelist:
        os.remove(f)
    
    lto_util.update_tar_xml_attributes(tarXmlDoc, tarname)
    xmlfile = open(sessionid+'-'+deviceid+'.xml', "w")
    prettydoc = tarXmlDoc.toprettyxml()
    #Hack to put id attribute at the start
    prettydoc = string.replace(prettydoc, '_id="', 'id="')
    xmlfile.write(prettydoc)
    xmlfile.close()
    
    #Ask user for confirmation to write media xml to database
    update = raw_input('Update database with session-media metadata? [y/n]: ')
    xml_media_filename = sessionid+'-'+deviceid+'-media.xml'
    if update == 'y':
        username = raw_input('username: ')
        password = getpass.getpass('password: ')
        if lto_util.db_add_media_xml(sessionid, deviceid, mediasXmlDoc, username, password):
            print 'database updated'
        else:
            print 'Failed to update database'
            lto_util.write_xml(mediasXmlDoc, xml_media_filename)
            print 'media xml saved to '+xml_media_filename
    else:
        lto_util.write_xml(mediasXmlDoc, xml_media_filename)
        print 'media xml saved to '+xml_media_filename

if __name__ == "__main__":
    main()

