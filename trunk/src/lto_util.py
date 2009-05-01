'''
Created on 14-Apr-2009

@author: kevala
'''

import os
import xml.dom.minidom
import subprocess
import string
import md5sum2
import base64 
import re
import sys
import distutils.file_util
import urllib
import httplib


def argument_checks(session_id, device_code, path):
    if not re.match(r'^[a-z]{1,3}-[0-9]{1,6}-[0-9]{1,2}$', session_id):
        print 'Argument Error: wrong format for session id. create-archive script terminated.'
        sys.exit(2)
    if not re.match(r'^(cam|aud|pho)-[0-9]{1,2}$', device_code):
        print 'Argument Error: wrong format for device code. create-archive script terminated.'
        sys.exit(2)
    if not os.path.exists(path):
        print 'Argument Error: '+path+' is not a valid path. create-archive script terminated.'
        sys.exit(2)
    
def config_checks(config):
    tar_archive_dir = config.get('Main', 'tar_archive_dir')
    proxy_media_dir = config.get('Main', 'proxy_media_dir')
    host = config.get('Connection', 'host')
    port = config.get('Connection', 'port')
    transcript_xmldb_root = config.get('Connection', 'transcript_xmldb_root')
    archive_format = config.get('Tar', 'archive_format')
    block_size_bytes = config.get('Tar', 'block_size_bytes')
    cmd = config.get('Par2', 'cmd')
    redundancy = config.getint('Par2', 'redundancy')
    num_files = config.getint('Par2', 'num_files')
    memory = config.getint('Par2', 'memory')
    video_types = config.get('MediaTypes', 'video_types')
    audio_types = config.get('MediaTypes', 'audio_types')
    image_types = config.get('MediaTypes', 'image_types')
    
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
    if not (int(block_size_bytes)%512 == 0):
        print 'Config Error: block size must be a multiple of 512. create-archive script terminated.'
        sys.exit(2)

#def db_session_id_exists(session_id):
    

def get_host_port(config):
    host = config.get('Connection', 'host')
    port = config.getint('Connection', 'port')
    return host+':'+str(port)

def get_transcript_xquery_url(config):
    transcriptXmlDbRoot = config.get('Connection', 'transcript_xmldb_root')
    return transcriptXmlDbRoot+'/xquery'
    
def create_db_session_media_xml(session_id, device_code):
    doc = xml.dom.minidom.Document()
    root = doc.createElement('mediaMetadata')
    doc.appendChild(root)
    devElement = doc.createElement('device')
    root.appendChild(devElement)
    devElement.setAttribute('code', device_code)
    devElement.setAttribute('sessionId', session_id)
    return doc

def create_tar_xml_doc(session_id, device_code):
    doc = xml.dom.minidom.Document()
    tarElement = doc.createElement('tar')
    doc.appendChild(tarElement)
    tarElement.setAttribute('sessionId', session_id)
    tarElement.setAttribute('deviceCode', device_code)
    return doc

def copy_media_file(filepath, new_filepath):
    print 'copying file '+filepath+' to '+new_filepath
    distutils.file_util.copy_file(filepath, new_filepath)

def create_referenced_items_file(filename, config, session_id):
    tarMeta = open(os.path.join(get_tar_build_dir(config), filename),'w')
    params = urllib.urlencode({'sessionIds': session_id})
    conn = httplib.HTTPConnection(get_host_port(config))
    try:
        conn.request('GET', get_transcript_xquery_url(config)+'/get-referenced-items.xql?'+params, None, {})
        response = conn.getresponse()
        tarMeta.writelines(response.read())
    except httplib.HTTPException, e:
        print e.msg
        print 'Unable to connect to database'
    else:
        conn.close()
        tarMeta.close()

def db_get_next_media_id(session_id, domain, config):
    event_type = session_id[:session_id.find('-')]
    params = urllib.urlencode({'domain': domain, 'eventType': event_type})
    conn = httplib.HTTPConnection(get_host_port(config))
    try:
        conn.request('GET', get_transcript_xquery_url(config)+'/get-next-media-id.xql?'+params, None, {})
        response = conn.getresponse()
        data = response.read()
        if '<exception>' in data:
            print get_xquery_exception_msg(data)
            print 'create-archive script terminated'
            sys.exit(2)
        else:
            return data
    except httplib.HTTPException, e:
        print e.msg
        print 'Unable to connect to database'
    else:
        conn.close()

def get_xquery_exception_msg(data):
    path = data[data.find('<path>')+6:data.find('</path>')]
    msg = data[data.find('<message>')+9:data.find('</message>')]
    return 'Xquery Error: \n'+path+'\n'+msg

def get_tar_build_dir(config):
    return config.get('Main', 'tar_archive_dir')+'/work'

def get_tar_blocking_factor(config):
    bs = config.getint('Tar', 'block_size_bytes')
    return int(bs)/512

def get_tar_format(config):
    return config.get('Tar', 'archive_format')

def media_in_type(file, domain, config):
    media_types = config.get('MediaTypes', domain+'_types').split(',')
    for type in media_types:
        if string.lower(file).endswith('.'+string.lower(type)):
            return True
    return False

def get_new_media_id(session_id, domain, config, previous_id):
    if not previous_id:
        id = db_get_next_media_id(session_id, domain, config)
    else:
        id = previous_id[:previous_id.find('-')]+'-'+str(int(previous_id[previous_id.find('-')+1:])+1)
    return id
        
def generate_db_media_xml_element(media_path, domain, media_id):
    if (domain == 'video'):
        if is_sony_xdcam_video(media_path):
            return get_xdcam_metadata_xml(media_path, domain, media_id)
        elif is_captured_dv_tape(media_path):
            return get_dv_tape_metadata_xml(media_path, domain, media_id)
    elif (domain == 'audio'):
        if is_fostex_audio(media_path):
            return get_fostex_audio_metadata_xml(media_path, domain, media_id)
        elif is_captured_md(media_path):
            return get_md_metadata_xml(media_path, domain, media_id)
    
            
def is_sony_xdcam_video(media_path):
    if 'BPAV/CLPR' in media_path and (string.lower(media_path)).endswith('.mp4'):
        return True
    return False

def is_captured_dv_tape(media_path):
    if (string.lower(media_path)).endswith('.mov'):
        return True
    return False

def is_fostex_audio(media_path):
    fostex_date_re = '^B[0-9]{2}h[0-9]{2}m[0-9]{2}s[0-9]{2}[a-z]{3}[0-9]{4}\.wav$'
    if re.match(fostex_date_re, get_filename(media_path)):
        return True
    return False

def is_captured_md(media_path):
    if (string.lower(media_path)).endswith('.wav'):
        return True
    return False

def get_filename(pathname):
    return pathname[str(pathname).rfind('/')+1:len(str(pathname))]

def get_path(pathname):
    return pathname[:str(pathname).rfind('/')]
    
def get_xdcam_metadata_xml(media_path, domain, media_id):
    supp_xml_path = media_path[0:-4]+'M01.XML'
    xfile = open(supp_xml_path)
    timestamp = get_xdcam_timestamp(xfile)
    original_id = get_xdcam_original_id(supp_xml_path)
    xfile.close()
    duration = get_media_duration(media_path)
    auto_split = get_xdcam_autosplit(media_path)
    attributes = {'timestamp':timestamp, 'originalId':original_id, 'duration':duration,'autoSplit':auto_split}
    return create_media_xml_element(domain, attributes, media_id)
    
def get_dv_tape_metadata_xml(media_path, domain, media_id):
    duration = get_media_duration(media_path)
    attributes = {'duration':duration}
    return create_media_xml_element(domain, attributes, media_id)
    
def create_media_xml_element(domain, attributes, media_id):
    #Using underscore is a hack to put id as the first attribute - due to crap implementation of minidom toxml() and toprettyxml()
    media_xml = '<'+domain+' _id="'+media_id+'" '
    for att in attributes.keys():
        media_xml += att+'="'+str(attributes[att])+'" '
    media_xml = media_xml.rstrip()
    media_xml += '/>'
    return media_xml

def get_xdcam_timestamp(xmlfile) :
    xmlfile.seek(0)
    for line in xmlfile:
        if 'CreationDate' in line:
            ts = line[line.find('"')+1:line.rfind('"')-6]
            return ts

def get_xdcam_original_id(xmlfile):
    return xmlfile[xmlfile.rfind('/')+1:-7]

def get_xdcam_autosplit(media_path):
    suffix = int(media_path[-6:-4])
    extn = media_path[-3:]
    next_suffix = '%02d' % (suffix +1)
    next_media_path = media_path[:-6]+next_suffix+'.'+extn
    if os.path.exists(next_media_path):
        return True
    return False

def get_media_duration(media_file):
    p = subprocess.Popen('ffmpeg -i '+media_file, shell=True, stderr=subprocess.PIPE)
    stdout_value = p.stderr.readlines()
    sts = os.waitpid(p.pid, 0)
    for line in stdout_value:
        if 'Duration:' in line:
            duration = line[line.find(':')+2:line.find(',')]
            return duration
    
def generate_par2_tar(config, new_filepath):
    par2_cmd = config.get('Par2', 'cmd')
    par2_redundancy = config.getint('Par2', 'redundancy')
    par2_numfiles = config.getint('Par2', 'num_files')
    par2_memory = config.getint('Par2', 'memory')
    
    fn = get_filename(new_filepath)
    path = get_path(new_filepath)
    
    print 'Generating PAR2 files for '+fn+'\n'
    p = subprocess.Popen(par2_cmd +' create -r'+str(par2_redundancy)+' -m'+str(par2_memory)+' -n'+str(par2_numfiles)+' '+new_filepath, shell=True)
    sts = os.waitpid(p.pid, 0)
    par2files = []
    for f in os.listdir(path):
        if str(f).startswith(fn) and str(f).endswith('.par2'):
            par2files.append(f)
            
    par2filesstr = string.join(par2files, ' ')
    p = subprocess.Popen('tar -c --format='+get_tar_format(config)+' -C '+path+' -f '+new_filepath+'.par2.tar '+par2filesstr, shell=True)
    sts = os.waitpid(p.pid, 0)
    for p in par2files:
        os.remove(os.path.join(path, p))
    
def generate_low_res(domain, filepath, dir):
    if (domain == 'video'):
        video_type = get_video_type(filepath)
        if video_type == ('DV_PAL' or 'DV_NTSC' or 'MPEG2_H-14'):
            preview_size = '384x288'
        elif video_type == 'MPEG2_HL':
            preview_size = '512x288'
        preview_suff = 'h261_'+preview_size
        preview_file = filepath[0:-3]+preview_suff+'.mp4'
        fn = get_filename(preview_file)
        p = subprocess.Popen('ffmpeg -y -i '+filepath+' -pass 1 -vcodec libx264 -vpre fastfirstpass -s '+preview_size+' -b 512k -bt 512k -threads 0 -f mp4 -an /dev/null && ffmpeg -y -i '+filepath+' -pass 2 -acodec libfaac -ab 128k -vcodec libx264 -vpre hq -s '+preview_size+' -b 512k -bt 512k -threads 0 -f mp4 '+dir+'/'+fn, shell=True)
        sts = os.waitpid(p.pid, 0)
        #Cleanup
        os.remove('ffmpeg2pass-0.log')
        os.remove('x264_2pass.log')
    elif (domain =='audio'):
        print 'lo_res ffmpeg call not yet defined. script terminated.'
        sys.exit(2)
    
def get_video_type(filepath):
    p = subprocess.Popen('ffmpeg -i '+filepath, shell=True, stderr=subprocess.PIPE)
    stdout_value = p.stderr.readlines()
    sts = os.waitpid(p.pid, 0)
    for line in stdout_value:
        if ('Video: dvvideo' in line) and ('720x576' in line):
            return 'DV_PAL'
        elif ('Video: dvvideo' in line) and ('720x480' in line):
            return 'DV_NTSC'
        elif ('Video: mpeg2video' in line) and ('1920x1080' in line):
            return 'MPEG2_HL'
        elif ('Video: mpeg2video' in line) and ('1440x1080' in line):
            return 'MPEG2_H-14'
    return False
        
def get_md5_hash(file):
    return md5sum2.sum(file)

def get_filesize(file):
    return os.path.getsize(file)
           
def db_add_media_xml(config, db_media_xml_doc, username, password):  
    deviceElement = db_media_xml_doc.getElementsByTagName('device')[0]
    session_id = deviceElement.getAttribute('sessionId')
    device_code = deviceElement.getAttribute('code')
    for mediaElem in deviceElement.childNodes:
        if mediaElem.nodeType == xml.dom.Node.ELEMENT_NODE:
            element_xml = str(mediaElem.toxml())
            params = urllib.urlencode({'sessionId': session_id, 'deviceCode': device_code, 'mediaXML': element_xml})
            base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
            authheader =  "Basic %s" % base64string
            headers = {'Authorization': authheader}
            conn = httplib.HTTPConnection(get_host_port(config))
            try:
                conn.request('GET', get_transcript_xquery_url(config)+'/import-media-element.xql?'+params, None, headers)
                response = conn.getresponse()
                data = response.read()
                print data
                if '<exception>' in data:
                    print get_xquery_exception_msg(data)
                    print 'create-archive script terminated'
                    sys.exit(2)
                else:
                    return data
            except httplib.HTTPException, e:
                print e.msg
                print 'Unable to connect to database'
            else:
                conn.close()

def append_tar_media_xml_element(doc, filepath, domain, media_id):
    mediaElement = doc.createElement(domain)
    mediaElement.setAttribute('_id', media_id)
    mediaElement.setAttribute('md5', get_md5_hash(filepath))
    mediaElement.setAttribute('size', str(get_filesize(filepath)))
    doc.documentElement.appendChild(mediaElement)
    par2TarElement = doc.createElement('par2Tar')
    par2TarElement.setAttribute('md5', get_md5_hash(filepath+'.par2.tar'))
    par2TarElement.setAttribute('size', str(get_filesize(filepath+'.par2.tar')))
    mediaElement.appendChild(par2TarElement)

def append_db_media_xml_element(doc, element_string):
    doc2 = xml.dom.minidom.parseString(element_string)
    media_element = doc2.documentElement
    deviceElement = doc.getElementsByTagName('device')[0]
    deviceElement.appendChild(media_element)

def update_block_xml_attributes(tar_xml_doc, line, config):
    filename = line[line.find(':')+2:-1]
    offset = int(line[6:line.find(':')])
    id = filename[filename.find('-')+1:filename.find('.')]
    for domain in ['video', 'audio', 'image']:
        mediaElems = tar_xml_doc.getElementsByTagName(domain)
        for e in mediaElems:
            if e.getAttribute('_id') == id:
                if media_in_type(filename, domain, config):
                    e.setAttribute('recordOffset', str(offset))
                elif filename.endswith('.par2.tar'):
                    par2Elem = e.getElementsByTagName('par2Tar')[0]
                    par2Elem.setAttribute('recordOffset', str(offset))
               
def update_tar_xml_root_attributes(config, doc, tar_name):               
    doc.documentElement.setAttribute('md5', get_md5_hash(get_tar_build_dir(config)+'/'+tar_name))
    doc.documentElement.setAttribute('size', str(get_filesize(get_tar_build_dir(config)+'/'+tar_name)))
    
def write_xml(xmldoc, filepath):
    f = open(filepath, "w")
    #Here we use toxml() instead of toprettyxml() since we need to re-parse this file in the create-virtual-tape script
    #re-applying toprettyxml() generates too much surrounding whitespace around each element in the final output file.
    #Hack to put id as the first attribute
    str = xmldoc.toxml()
    str = string.replace(str, '_id="', 'id="')
    f.write(str)
    f.close()
