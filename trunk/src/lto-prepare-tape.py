'''
Created on 15-Apr-2009

@author: kevala
'''

import os
import sys
import xml.dom.minidom
import datetime
import urllib
import urllib2
import lto_util
import base64
import getpass


def append_tar_element(doc, filepath, position, block):
    tarXmlDoc = xml.dom.minidom.parse(filepath)
    tarElement = tarXmlDoc.documentElement
    doc.documentElement.appendChild(tarElement)
    tarElement.setAttribute('position', str(position))
    tarElement.setAttribute('block', str(block))
    
def create_tape_xml(datetime, blocksize):
    doc = xml.dom.minidom.Document()
    tapeElement = doc.createElement('tape')
    doc.appendChild(tapeElement)
    tapeElement.setAttribute('timestamp', datetime)
    tapeElement.setAttribute('blocksize', str(blocksize)+'K')
    return doc

def db_import_tape_xml(tapeXmlDoc, username, password, host='localhost:8080'):
    tapeXML = str(tapeXmlDoc.toxml())
    tapeXMLencoded = urllib.quote(tapeXML)
    url = 'http://'+host+'/exist/rest//db/lto4isha/xquery/import-tape-element.xql?tapeXML='+tapeXMLencoded
    req = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    authheader =  "Basic %s" % base64string
    req.add_header("Authorization", authheader)
    try:
        handle = urllib2.urlopen(req)
    except IOError, e:
        print e.code
        print e.headers
        return False
    return handle.read()

def update_tape_xml(doc, id):
    tapeElement = doc.documentElement
    tapeElement.setAttribute('_id', id)
    return doc
        

def main():

    host = 'localhost:8080'
    
    lto_home = '/lto-stage'
    tape_home = lto_home+'/tapes'
    work_home = lto_home+'/work'
    tar_home = lto_home+'/tars'
    
    blocksize = 128
    max_tape_size_bytes = 370 * 1024 * 1024 * 1024
    
    #Allow 100MB space for tape index
    tape_index_size_bytes = 100 * 1024 * 1024
    
    today = datetime.datetime.now()
    format_today = today.strftime("%Y-%m-%dT%H:%M:%S")
    
    totalSize = 0
    for file in os.listdir(work_home):
        s = lto_util.get_filesize(os.path.join(work_home, file))
        totalSize += s
        
    if totalSize > max_tape_size_bytes:
        print 'Total file size of '+work_home+' directory ('+str(totalSize)+') exceeds '+str(max_tape_size_bytes)+' bytes.'
        sys.exit(1)
    else:
        print 'Total file size to be archived: '+str(totalSize)+' bytes'
        
    #Need to put checks that each tar file has a corresponding xml file - correctly named
    
    tapeXmlDoc = create_tape_xml(format_today, blocksize)
    
    tars = []
    for t in os.listdir(work_home):
        if t.endswith('.tar'):
            tars.append(t)
            tars.sort()
            
    current_block = int(tape_index_size_bytes/(blocksize * 512)) +1;
            
    for index, tar in enumerate(tars):
        tar_name = tar[0:-4]
        position = index+2
        size = lto_util.get_filesize(os.path.join(work_home, tar))
        block_bytes = blocksize * 512
        file_blocks = int(size/block_bytes) 
        xml_path = os.path.join(work_home, tar_name+'.xml')
        append_tar_element(tapeXmlDoc, xml_path, position, current_block)
        current_block += file_blocks + 1
        
    #Import tape.xml to the xml database
    username = raw_input('username: ')
    password = getpass.getpass('password: ')
    tape_id = db_import_tape_xml(tapeXmlDoc, username, password)
    if tape_id:
        print 'database updated'
    else:
        print 'Failed to update database. create-virtual-tape script terminated'
        sys.exit(1)
    
    update_tape_xml(tapeXmlDoc, tape_id)
    tape_dir = tape_home+'/pending/'+tape_id
    os.mkdir(tape_dir)
    lto_util.write_xml(tapeXmlDoc, tape_dir+'/'+tape_id+'.xml')
    
         
         
if __name__ == "__main__":
    main()