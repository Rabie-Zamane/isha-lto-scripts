'''
Created on 14-Apr-2009

@author: kevala
'''

import os
import xml.dom.minidom
import subprocess
import string
import base64 
import re
import sys
import distutils.file_util
import urllib
import httplib
import shutil
import datetime
import hashlib

def get_script_name():
    return get_filename(sys.argv[0])

def path_check(path):
    if not os.path.exists(path):
        print 'Path Error: '+path+' does not exist.' 
        print get_script_name()+' script terminated.'
        sys.exit(2)
        
def exec_url_xquery(config, collection, query):
    try:
        conn = httplib.HTTPConnection(get_host_port(config))
        params = urllib.urlencode({'_query': query})
        conn.request('GET', collection+'?'+params, None, {})
        response = conn.getresponse()
        return response.read()
    except httplib.HTTPException, e:
        print 'Unable to execute xquery'
    else:
        conn.close()
        
def get_parsed_xquery_value(result):
    doc = xml.dom.minidom.parseString(result) 
    node = doc.getElementsByTagName('exist:value')[0]
    return node.firstChild.nodeValue
    
def valid_chars(string):
    return re.match(r'^[a-zA-Z0-9-_]+$', string)
    
def config_checks(config):
    tar_archive_dir = config.get('Dirs', 'tar_archive_dir')
    proxy_media_dir = config.get('Dirs', 'proxy_media_dir')
    host = config.get('Connection', 'host')
    port = config.get('Connection', 'port')
    transcript_xmldb_root = config.get('Connection', 'transcript_xmldb_root')
    archive_format = config.get('Tar', 'archive_format')
    block_size_bytes = config.get('Tape', 'block_size_bytes')
    max_gb = config.get('Tape', 'max_gb')
    min_gb = config.get('Tape', 'min_gb')
    index_size_mb = config.get('Tape', 'index_size_mb')
    cmd = config.get('Par2', 'cmd')
    redundancy = config.getint('Par2', 'redundancy')
    num_files = config.getint('Par2', 'num_files')
    memory = config.getint('Par2', 'memory')
    
    if not os.path.exists(tar_archive_dir):
        print 'Config Error: tar_archive_dir is not a valid path. create-archive script terminated.'
        sys.exit(2)
    if not os.path.exists(proxy_media_dir):
        print 'Config Error: proxy_media_dir is not a valid path. create-archive script terminated.'
        sys.exit(2)
    if not (host == 'localhost' or re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', host)):
        print 'Config Error: wrong format for host. create-archive script terminated.'
        sys.exit(2)
    if not (int(port) >= 0 and int(port) <= 65535):
        print 'Config Error: wrong format for port. create-archive script terminated.'
        sys.exit(2)
    if not (block_size_bytes.isdigit()):
        print 'Config Error: block_size_bytes must be an integer. create-archive script terminated.'
        sys.exit(2) 
    if not (int(block_size_bytes)%1024 == 0):
        print 'Config Error: block size must be a multiple of 1024. create-archive script terminated.'
        sys.exit(2)   
    if not (max_gb.isdigit()):
        print 'Config Error: max_gb must be an integer. create-archive script terminated.'
        sys.exit(2)   
    if not (min_gb.isdigit()):
        print 'Config Error: min_gb must be an integer. create-archive script terminated.'
        sys.exit(2) 
    

def get_host_port(config):
    host = config.get('Connection', 'host')
    port = config.getint('Connection', 'port')
    return host+':'+str(port)

def get_transcript_url(config):
    return config.get('Connection', 'transcript_xmldb_root')

def get_lto_url(config):
    return config.get('Connection', 'lto_xmldb_root')

def get_blocksize(config):
    return config.get('Tape', 'block_size_bytes')

def get_tape_device(config):
    return config.get('Tape', 'device')
    
def copy_file(filepath, new_filepath):
    print 'copying file '+filepath+' to '+new_filepath
    distutils.file_util.copy_file(filepath, new_filepath)
        
def move(filepath, dirpath):
    #Using native command line tool mv - since shutils.move copies and renames even for files on the same file system !! :-(
    if not os.path.exists(filepath):
        print 'IO Error: File '+filepath+' does not exist.'
        print lto_util.get_script_name()+' script terminated.'
    if not os.path.isdir(dirpath):
        print 'IO Error: File '+dirpath+' is not a directory.'
        print lto_util.get_script_name()+' script terminated.'
    p = subprocess.Popen('mv '+filepath+' '+dirpath, shell=True, stderr=subprocess.PIPE)
    sts = os.waitpid(p.pid, 0)
    terminate_on_error(p.stderr.read())

def get_xquery_exception_msg(data):
    path = data[data.find('<path>')+6:data.find('</path>')]
    msg = data[data.find('<message>')+9:data.find('</message>')]
    return 'Xquery Error: \n'+path+'\n'+msg

def delete_dir_content(dir):
    print '\nDeleting contents of '+dir
    try:
        shutil.rmtree(dir)
        os.mkdir(dir)
    except IOError:
        print 'IO Error: Unable to delete content of '+dir
        print get_script_name()+' script terminated.'
        sys.exit(2)
    else:
        print 'OK'
        
def get_temp_dir(config):
    return config.get('Dirs', 'temp_dir')

def get_tar_build_dir(config):
    return config.get('Dirs', 'temp_dir')+'/build-tar'

def get_tape_build_dir(config):
    return config.get('Dirs', 'virtual_tape_dir')+'/build'

def get_tape_verify_dir(config):
    return config.get('Dirs', 'temp_dir')+'/verify-tape'

def get_tape_pending_dir(config):
    return config.get('Dirs', 'virtual_tape_dir')+'/pending'

def get_tape_written_dir(config):
    return config.get('Dirs', 'virtual_tape_dir')+'/written'

def get_proxy_media_dir(config):
    return config.get('Dirs', 'proxy_media_dir')

def get_tar_blocking_factor(config):
    bs = config.getint('Tape', 'block_size_bytes')
    return int(bs)/512

def get_tar_format(config):
    return config.get('Tar', 'archive_format')

def get_filename(pathname):
    return pathname[str(pathname).rfind('/')+1:]

def get_path(pathname):
    return pathname[:str(pathname).rfind('/')]

def get_file_extn(pathname):
    return pathname[str(pathname).rfind('.')+1:]
    
def create_dir(pathname):
    if os.path.exists(pathname):
        shutil.rmtree(pathname)
    os.makedirs(pathname)
    
def get_md5_hash(file):
    bufsize = 8096
    fp = open(file, 'rb')
    m = hashlib.md5()
    while True:
        data = fp.read(bufsize)
        if not data:
            return m.hexdigest()
        m.update(data)
    
def compare(f1, f2):
    bufsize = 8096
    fp1 = open(f1, 'rb')
    fp2 = open(f2, 'rb')
    m = hashlib.md5()
    while True:
        b1 = fp1.read(bufsize)
        b2 = fp2.read(bufsize)
        if b1 != b2:
            return False
        if not b1:
            return m.hexdigest()
        m.update(b1)
 
def get_filesize(file):
    return os.path.getsize(file)
           
def write_xml(xmldoc, filepath):
    f = open(filepath, "w")
    #Here we use toxml() instead of toprettyxml() since we need to re-parse this file in the create-virtual-tape script
    #re-applying toprettyxml() generates too much surrounding whitespace around each element in the final output file.
    #Hack to put id as the first attribute
    str = xmldoc.toxml()
    str = string.replace(str, '_id="', 'id="')
    f.write(str)
    f.close()

def get_dir_total_size(dir):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir):
        for f in filenames:
            total_size += get_filesize(os.path.join(dirpath, f))
    return total_size

def get_curr_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%dT%H:%M:%S")

def terminate_on_error(stderr):
    if not stderr:
        print 'OK'
    else:
        print 'Error: '+stderr
        print get_script_name()+' script terminated.'
        sys.exit(2)
        
def move_virtual_tape_dir(config, tape_id, src_stage, dest_stage):
    dest = config.get('Dirs', 'virtual_tape_dir')+'/'+dest_stage
    src = config.get('Dirs', 'virtual_tape_dir')+'/'+src_stage+'/'+tape_id
    try: 
        print 'Moving virtual tape folder '+src+' to '+dest 
        move(src, dest)
    except Exception, e:
        print '\nUnable to move '+src+' to '+dest 
        print get_script_name()+' script terminated.'
        sys.exit(2)

    