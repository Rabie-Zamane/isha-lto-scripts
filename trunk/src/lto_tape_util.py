'''
Created on 03-May-2009

@author: kevala
'''

import os
import sys
import xml.dom.minidom
import lto_util


def check_tape_build_dir_contents(dir):
    for f in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, f)):
            print 'The tape build directory: '+dir+' must not contain any sub-directories.'
            print '\ncreate-virtual-tape script terminated.'
            sys.exit(2)
        elif not (f.endswith('.tar') or f.endswith('.xml')):
            print 'The tape build directory: '+dir+' contains unidentified files.'
            print '\ncreate-virtual-tape script terminated.'
            sys.exit(2)
        elif f.endswith('.tar'):
            fid = f[:-4]
            if not os.path.exists(os.path.join(dir, fid+'.xml')):
                print 'The tape build directory: '+dir+' contains tar files without matching xml files.'
                print '\ncreate-virtual-tape script terminated.'
                sys.exit(2)
        elif f.endswith('.xml'):
            fid = f[:-4]
            if not os.path.exists(os.path.join(dir, fid+'.tar')):
                print 'The tape build directory: '+dir+' contains xml files without matching tar files.'
                print '\ncreate-virtual-tape script terminated.'
                sys.exit(2)
                
def check_tape_build_size(config):
    dir = lto_util.get_tape_build_dir(config)
    min_gbs = config.getint('Tape', 'min_gb')
    max_gbs = config.getint('Tape', 'max_gb')
    min_size = int(min_gbs)*1024*1024*1024
    max_size = int(max_gbs)*1024*1024*1024
    index_size_mb = config.getint('Tape', 'index_size_mb')
    index_size = index_size_mb*1024*1024
    size = lto_util.get_dir_total_size(dir) + index_size
    size_gb = float(size)/(1024*1024*1024)
    
    if size > max_size:
        print 'The total size of the files in the tape build directory: '+dir+' is over the maximum limit of '+str(max_gbs)+'GB.'
        print '\ncreate-virtual-tape script terminated.'
        sys.exit(2)    
    elif size < min_size:
        print 'The total size of the files in the tape build directory: '+dir+' is under the minimum limit of '+str(min_gbs)+'GB.'
        print '\ncreate-virtual-tape script terminated.'
        sys.exit(2)
    else:
        print 'Total virtual tape size: '+'%3.2f'%size_gb+'GB'
        
def create_tape_xml_doc(datetime_str, config):
    doc = xml.dom.minidom.Document()
    tapeElement = doc.createElement('tape')
    doc.appendChild(tapeElement)
    block_size_bytes = int(config.get('Tape', 'block_size_bytes'))
    block_size_kbs = block_size_bytes/1024
    tapeElement.setAttribute('timestamp', datetime_str)
    tapeElement.setAttribute('blockSize', str(block_size_kbs)+'k')
    return doc

def create_tape_index(tape_xml_doc, config):
    tars = []
    for t in os.listdir(lto_util.get_tape_build_dir(config)):
        if t.endswith('.tar'):
            tars.append(t)
    tars.sort()
        
    block_size_bytes = int(config.get('Tape', 'block_size_bytes'))    
    tape_index_size_bytes = int(config.get('Tape', 'tape_index_size_bytes'))
    current_block = tape_index_size_bytes/block_size_bytes +1
        
    for index, tar in enumerate(tars):
        tar_name = tar[0:-4]
        position = index+2
        size = lto_util.get_filesize(os.path.join(lto_util.get_tape_build_dir(config), tar))
        blocks = int(size/block_size_bytes) 
        tar_xml_path = os.path.join(lto_util.get_tape_build_dir(config), tar_name+'.xml')
        append_tar_element_to_tape_xml_doc(tape_xml_doc, tar_xml_path, position, current_block)
        current_block += blocks + 1

def append_tar_element_to_tape_xml_doc(tape_xml_doc, tar_xml_path, position, current_block):
    tar_xml_doc = xml.dom.minidom.parse(tar_xml_path)
    tarElement = tar_xml_doc.documentElement
    tape_xml_doc.documentElement.appendChild(tarElement)
    tarElement.setAttribute('position', str(position))
    tarElement.setAttribute('block', str(current_block)) 
    
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
          
                    
