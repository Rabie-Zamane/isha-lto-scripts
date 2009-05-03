'''
Created on 03-May-2009

@author: kevala
'''

import os
import sys
import xml.dom.minidom
import urllib
import httplib
import base64
import getpass
import string
import shutil
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
        print 'Virtual tape size: '+'%3.2f'%size_gb+'GB'
        
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
    index_size_mb = int(config.get('Tape', 'index_size_mb'))
    index_size_bytes = index_size_mb * 1024*1024
    current_block = index_size_bytes/block_size_bytes +1
        
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
    
def db_import_tape_xml(config, tape_xml_doc):
    tape_xml = str(tape_xml_doc.toxml())
    print '\nImporting tape index to database:\n'
    username = raw_input('username: ')
    password = getpass.getpass('password: ')
    base64string = string.strip(base64.encodestring('%s:%s' % (username, password)))
    authheader =  "Basic %s" % base64string
    headers = {"Authorization": authheader, "Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    params = urllib.urlencode({'tapeXML': tape_xml})
    conn = httplib.HTTPConnection(lto_util.get_host_port(config))
    try:
        conn.request('POST', lto_util.get_lto_url(config)+'/xquery/import-tape-element.xql', params, headers)
        response = conn.getresponse()
        data = response.read()
        if '<exception>' in data:
            print lto_util.get_xquery_exception_msg(data)
            print 'Unable to update database.'
            print 'create-virtual-tape script terminated.'
            sys.exit(2)
        elif 'HTTP ERROR: 404' in data:
            print '\nHTTP ERROR: 404'
            print data[data.find('<title>')+7:data.find('</title>')]
            print 'create-virtual-tape script terminated.'
            sys.exit(2)
        elif response.status == 401 and response.reason == 'Unauthorized':
            print 'Authentication Failed.'
            print 'create-virtual-tape script terminated.'
            sys.exit(2)
        else:
            print '\nDatabase updated (tape id: '+data+').'
    except httplib.HTTPException, e:
        print e.msg
        print 'Unable to connect to database'
        print 'create-virtual-tape script terminated.'
        conn.close()
        sys.exit(2)
    else:
        conn.close()    
        return data  
        
def update_tape_xml(doc, id):
    tapeElement = doc.documentElement
    tapeElement.setAttribute('_id', id)
    return doc

def write_tape_xml_file(config, tape_xml_doc, tape_id):
    tape_xml_filepath = lto_util.get_tape_build_dir(config)+'/'+tape_id+'.xml'
    lto_util.write_xml(tape_xml_doc, tape_xml_filepath)
    
def move_virtual_tape_files(config, tape_id):
    dest = config.get('Dirs', 'virtual_tape_dir')+'/pending/'+tape_id
    try:
        os.mkdir(dest)
        print 'Created virtual tape directory: '+dest
    except os.OSError, e:
        print 'Unable to create virtual tape directory: '+dest
        print 'create-archive script terminated.'
        sys.exit(2)
    tb = lto_util.get_tape_build_dir(config)
    for f in os.listdir(tb):
        try:
            shutil.move(tb+'/'+f, dest)
        except Exception, e:
            print 'Unable to move files to: '+dest
            print 'create-archive script terminated.'
            sys.exit(2)
    print 'Files transferred from '+lto_util.get_tape_build_dir(config)+' to '+dest