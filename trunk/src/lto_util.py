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


def check_archive_args(options):
    if options.session_id == None or options.session_id =="":
        print 'Argument Error: session id not specified. create-archive script terminated.'
        sys.exit(2)
    if options.device_code == None or options.device_code =="":
        print 'Argument Error: device code not specified. create-archive script terminated.'
        sys.exit(2)
    if options.path == None or options.path =="":
        print 'Argument Error: media path not specified. create-archive script terminated.'
        sys.exit(2)

def get_script_name():
    return get_filename(sys.argv[0])

def media_path_check(path):
    if not os.path.exists(path):
        print 'Argument Error: '+path+' is not a valid path. create-archive script terminated.'
        sys.exit(2)

def path_check(path):
    if not os.path.exists(path):
        print 'Path Error: '+path+' does not exist.' 
        print get_script_name()+' script terminated.'
        sys.exit(2)

def get_media_category(config, path):
    last_dir = path[path.rfind('/')+1:]
    
    xdcamDir = config.get('CategoryFolders', 'sony-xdcam')
    dvDir = config.get('CategoryFolders', 'video')
    fostexDir = config.get('CategoryFolders', 'fostex-audio')
    mdDir = config.get('CategoryFolders', 'audio')
    
    if last_dir == xdcamDir:
        return 'sony-xdcam'
    elif last_dir == dvDir:
        return 'video'
    elif last_dir == fostexDir:
        return 'fostex-audio'
    elif last_dir == mdDir:
        return 'audio'
    else:
        print 'Path must terminate with one of the following directory names: '+xdcamDir+', '+dvDir+', '+fostexDir+', '+mdDir
        print get_script_name()+' script terminated.'
        sys.exit(2)
    
def media_file_types_check(config, category, path):
    category_filetypes = config.get('CategoryFileTypes', category).split(',')
    media_file_count = 0
    non_category_files = []
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            if media_in_domain(file, 'video', config) or media_in_domain(file, 'audio', config) or media_in_domain(file, 'image', config):
                if not media_in_category(file, category, config): 
                    non_category_files.append(os.path.join(dirpath, file))
                else: 
                    media_file_count += 1
                                              
    if (len(non_category_files) > 0):
        print 'WARNING: The following unexpected media files were found in the folder: '+path+'\n'
        for f in non_category_files:
            print f    
        print '\nExpecting only '+string.upper(string.join(category_filetypes, ','))+' files for "'+category+'" category.'
        print '\nNOTE: This situation should only occur if when one device has generated multiple media formats. (e.g. a video camera taking stills/audio as well as video)'
        print 'Usually this indicates that the files have been misplaced, in which case the user should manually remove them before re-running the script.\n'
        proceed = raw_input('Do you still want to proceed, including these files in the archive? [y/n]: ')
        if proceed == 'y':
            return
        else:
            print get_script_name()+' script terminated.'
            sys.exit(2)
            
    elif media_file_count == 0:
        print 'No recognised media files were found in: '+path
        print get_script_name()+' script terminated.'
        sys.exit(2)
    
def exec_url_xquery_boolean(config, collection, query):
    try:
        conn = httplib.HTTPConnection(get_host_port(config))
        params = urllib.urlencode({'_query': query})
        conn.request('GET', get_transcript_url(config)+'/'+collection+'?'+params, None, {})
        response = conn.getresponse()
        data = response.read()
        if '<exist:value exist:type="xs:boolean">true</exist:value>' in data:
            return True
        else:
            return False
    except httplib.HTTPException, e:
        print 'Unable to execute xquery'
    else:
        conn.close()
        
def valid_chars(string):
    return re.match(r'^[a-zA-Z0-9-_]+$', string)
        
def session_device_check(config, session_id, device_code):
    if not valid_chars(session_id):
        print 'Argument Error: Invalid characters used in session id. create-archive script terminated.'
        sys.exit(2)
    if not valid_chars(device_code):
        print 'Argument Error: Invalid characters used in device_code. create-archive script terminated.'
        sys.exit(2)
        
    session_exists_qry = 'exists(/session[@id="'+session_id+'"])'
    device_exists_qry = 'exists(//deviceCode[@id="'+device_code+'"])'
    media_exists_for_session_device_qry = 'exists(/session[@id="'+session_id+'"]//device[@code="'+device_code+'"]/*)'
    
    if not exec_url_xquery_boolean(config, 'data', session_exists_qry):
        print 'session id: '+session_id+' does not yet exist. create-archive-script terminated.'
        sys.exit(2)
    if not exec_url_xquery_boolean(config, 'reference', device_exists_qry):
        print 'device code: '+device_code+' does not exist. create-archive-script terminated.'
        sys.exit(2)
    if exec_url_xquery_boolean(config, 'data', media_exists_for_session_device_qry):
        print 'At least one media item has already been associated with session: '+session_id+' and device: '+device_code
        print
        print 'To see the associated media items for this session open the following link in your browser:'
        print 'http://'+get_host_port(config)+get_transcript_url(config)+'/data?_query=/session[@id="'+session_id+'"]//mediaMetadata'
        print
        cont = raw_input('Are you sure you want to continue? [y/n]: ')
        if cont == 'y':
            return 
        else:
            print get_script_name()+' script terminated.'
            sys.exit(2)
    
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

def get_new_filepath(config, domain, media_id, filepath):
    tb = get_tar_build_dir(config)
    extn = string.lower(get_file_extn(filepath))
    new_fp = tb+'/'+domain+'-'+media_id+'.'+extn
    return new_fp

def copy_media_file(filepath, new_filepath):
    print 'copying file '+filepath+' to '+new_filepath
    distutils.file_util.copy_file(filepath, new_filepath)
    
def move_tar_files(config, session_id, device_code):
    tb = get_tar_build_dir(config)
    archive_id = session_id+'-'+device_code
    tar = tb+'/'+archive_id+'.tar'
    xml = tb+'/'+archive_id+'.xml'
    dest = config.get('Dirs', 'tar_archive_dir')
    try: 
        print '\nMoving '+archive_id+'.tar to '+dest 
        move(tar, dest)
        print '\nMoving '+archive_id+'.xml to '+dest 
        move(xml, dest)
    except Exception, e:
        print '\nUnable to move archive files to: '+dest
        print get_script_name()+' script terminated.'
        sys.exit(2)
        
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

def create_referenced_items_file(config, session_id):
    tarMeta = open(os.path.join(get_tar_build_dir(config), 'referenced-items.xml'),'w')
    params = urllib.urlencode({'sessionIds': session_id})
    conn = httplib.HTTPConnection(get_host_port(config))
    try:
        conn.request('GET', get_transcript_url(config)+'/xquery/get-referenced-items.xql?'+params, None, {})
        response = conn.getresponse()
        tarMeta.writelines(response.read())
    except httplib.HTTPException, e:
        print 'Unable to connect to database'
    else:
        conn.close()
        tarMeta.close()

def db_get_next_media_id(session_id, domain, config):
    event_type = session_id[:session_id.find('-')]
    params = urllib.urlencode({'domain': domain, 'eventType': event_type})
    conn = httplib.HTTPConnection(get_host_port(config))
    try:
        conn.request('GET', get_transcript_url(config)+'/xquery/get-next-media-id.xql?'+params, None, {})
        response = conn.getresponse()
        data = response.read()
        if '<exception>' in data:
            print get_xquery_exception_msg(data)
            print get_script_name()+' script terminated.'
            sys.exit(2)
        else:
            return data
    except httplib.HTTPException, e:
        print 'Unable to connect to database'
    else:
        conn.close()

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
    

def get_tar_build_dir(config):
    return config.get('Dirs', 'tar_archive_dir')+'/work'

def get_tape_build_dir(config):
    return config.get('Dirs', 'virtual_tape_dir')+'/work'

def get_tape_pending_dir(config):
    return config.get('Dirs', 'virtual_tape_dir')+'/pending'

def get_proxy_media_dir(config):
    return config.get('Dirs', 'proxy_media_dir')

def get_tar_blocking_factor(config):
    bs = config.getint('Tape', 'block_size_bytes')
    return int(bs)/512

def get_tar_format(config):
    return config.get('Tar', 'archive_format')

def media_in_domain(file, domain, config):
    domain_types = config.get('DomainFileTypes', domain).split(',')
    for type in domain_types:
        if string.lower(file).endswith('.'+string.lower(type)):
            return True
    return False

def media_in_category(file, category, config): 
    category_filetypes = config.get('CategoryFileTypes', category).split(',')
    for type in category_filetypes:
        if string.lower(file).endswith('.'+string.lower(type)):
            return True
    return False

def db_media_id_exists(domain, id, config):
    media_id_exists_for_domain_qry = 'exists(/session//mediaMetadata//'+domain+'[@id="'+id+'"])'
    return exec_url_xquery_boolean(config, 'data', media_id_exists_for_domain_qry)

def generate_new_id(session_id, domain, config, previous_id):
    if not previous_id:
        return db_get_next_media_id(session_id, domain, config)
    else:
        return previous_id[:previous_id.find('-')]+'-'+str(int(previous_id[previous_id.find('-')+1:])+1)

def get_id_from_filename(filepath, domain, config):
    fn = get_filename(filepath)
    id = string.lower(fn[:fn.rfind('.')])
    if re.match('^[a-z]{1,3}-?[0-9]{1,7}$', id):
        alpha = re.match('^[a-z]+', id)
        alpha_index = alpha.end()
        num = re.match('[0-9]+$', id)
        num_index = num.start()
        alpha_part = id[:alpha_index]
        #This is to remove any leading zeros (which will prevent ids from matching)
        num_part = int(id[num_index:])
        if num_part == 0:
            print 'Media filename cannot have a zero digit component.'
            print get_script_name()+' script terminated.'
            sys.exit(2)
        #Insert hyphen if un-hyphenated
        id = alpha_part+'-'+str(num_part)
        if db_media_id_exists(domain, id, config):
            print 'The '+domain+' media id: '+id+' has already been used.'
            print get_script_name()+' script terminated.'
            sys.exit(2)
    else:
        print 'Captured media filename: '+fn+' in wrong format.'
        print get_script_name()+' script terminated.'
        sys.exit(2)
    return id   

def get_new_media_id(session_id, domain, category, config, previous_id, filepath):
    if category == 'sony-xdcam':
        id = generate_new_id(session_id, domain, config, previous_id)
    elif category == 'video':
        id = get_id_from_filename(filepath, domain, config)
    elif category == 'fostex-audio':
        id = generate_new_id(session_id, domain, config, previous_id)
    elif category == 'audio':
        id = get_id_from_filename(filepath, domain, config)
    else:
        print 'Undefined media category: '+category
        print get_script_name()+' script terminated.'
        sys.exit(2)
    return id
        
def generate_db_media_xml_element(media_path, domain, category, media_id, config):
    if category == 'sony-xdcam' and media_in_category(media_path, category, config):
        mfile = open(media_path, 'r')
        num_bytes_mp4_xml_data = 1143
        mfile.seek(-num_bytes_mp4_xml_data, 2)
        mp4xml = mfile.read()
        timestamp = get_sonyxdcam_timestamp(mp4xml)
        original_id = get_original_id(media_path)
        duration = get_media_duration(media_path)
        auto_split = get_autosplit(media_path)
        attributes = {'timestamp':timestamp, 'originalId':original_id, 'duration':duration,'autoSplit':auto_split}    
    elif category == 'video' and media_in_category(media_path, category, config):
        duration = get_media_duration(media_path)
        attributes = {'originalId':original_id, 'duration':duration}
    elif category == 'fostex-audio' and media_in_category(media_path, category, config):
        timestamp = get_fostexaudio_timestamp(media_path)
        original_id = get_original_id(media_path)
        duration = get_media_duration(media_path)
        attributes = {'timestamp':timestamp, 'originalId':original_id, 'duration':duration}
    elif category == 'audio'and media_in_category(media_path, category, config):
        duration = get_media_duration(media_path)
        attributes = {'originalId':original_id,'duration':duration}
    else:
        original_id = get_original_id(media_path)
        attributes = {'originalId':original_id}
    return create_media_xml_element(domain, attributes, media_id)

def get_filename(pathname):
    return pathname[str(pathname).rfind('/')+1:]

def get_path(pathname):
    return pathname[:str(pathname).rfind('/')]

def get_file_extn(pathname):
    return pathname[str(pathname).rfind('.')+1:]
    
def create_media_xml_element(domain, attributes, media_id):
    #Using underscore is a hack to put id as the first attribute - due to crap implementation of minidom toxml() and toprettyxml()
    media_xml = '<'+domain+' _id="'+media_id+'" '
    for att in attributes.keys():
        media_xml += att+'="'+str(attributes[att])+'" '
    media_xml = media_xml.rstrip()
    media_xml += '/>'
    return media_xml

def get_sonyxdcam_timestamp(xml):
    start = xml.find('<CreationDate value="')+21
    return xml[start:start+19]

def get_fostexaudio_timestamp(filepath):
    fn = get_filename(filepath)
    year = fn[15:19]
    month_word = fn[12:15]
    day = fn[10:12]
    hr = fn[1:3]
    min = fn[4:6]
    sec = fn[7:9]
    months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
    month = '%02d' % (months.index(month_word) + 1)
    dt = year+'-'+month+'-'+day+'T'+hr+':'+min+':'+sec
    return dt 

def get_original_id(file):
    return file[file.rfind('/')+1:-4]

def get_autosplit(media_path):
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
    stderr_value = p.stderr.readlines()
    sts = os.waitpid(p.pid, 0)
    for line in stderr_value:
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
    bufsize = 8096
    fp = open(file, 'rb')
    m = hashlib.md5()
    try:
        while 1:
            data = fp.read(bufsize)
            if not data:
                break
            m.update(data)
    except IOError, msg:
        print 'MD5 IO Error: '+msg+'\n' 
        print lto_util.get_script_name()+' script terminated.'
        sys.exit(2)
    return m.hexdigest()
 
def get_filesize(file):
    return os.path.getsize(file)
           
def db_add_media_xml(config, db_media_xml_doc, username, password):  

    deviceElement = db_media_xml_doc.getElementsByTagName('device')[0]
    session_id = deviceElement.getAttribute('sessionId')
    device_code = deviceElement.getAttribute('code')
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    authheader =  "Basic %s" % base64string
    headers = {'Authorization': authheader}
    conn = httplib.HTTPConnection(get_host_port(config))
   
    if len(deviceElement.childNodes) == 0:
        print 'Internal Error: No session-media xml nodes generated.'
        print 'create-archive script terminated.'
        sys.exit(2)
    
    for mediaElem in deviceElement.childNodes:
        if mediaElem.nodeType == xml.dom.Node.ELEMENT_NODE:
            element_xml = str(mediaElem.toxml())
            #Hack to put id as the first attribute
            element_xml = string.replace(element_xml, '_id="', 'id="')
            params = urllib.urlencode({'sessionId': session_id, 'deviceCode': device_code, 'mediaXML': element_xml})
            try:
                conn.request('GET', get_transcript_url(config)+'/xquery/import-media-element.xql?'+params, None, headers)
                response = conn.getresponse()
                data = response.read()
                if '<exception>' in data:
                    print get_xquery_exception_msg(data)
                    print 'create-archive script terminated'
                    return False
                elif response.status == 401 and response.reason == 'Unauthorized':
                    print 'Authentication Failed.'
                    return False
            except httplib.HTTPException, e:
                print 'Unable to connect to database'
    conn.close()
    return True

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
                if media_in_domain(filename, domain, config):
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

    