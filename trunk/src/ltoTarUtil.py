
import os
import subprocess
import string
import getpass
import xml.dom.minidom
import sys
import urllib
import httplib
import re
import base64
import ltoUtil

def check_tar_args(args):
    if args[0] == None or args[0] =="":
        print 'Session id not specified.' 
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if args[1] == None or args[1] =="":
        print 'Device code not specified.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if args[2] == None or args[2] =="":
        print 'Media path not specified.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
        
def get_media_category(config, path):
    if path.endswith('/'):
        path = path[:-1]
    last_dir = path[path.rfind('/')+1:]
    
    xdcamDir = config.get('CategoryFolders', 'sony-xdcam')
    dvDir = config.get('CategoryFolders', 'video')
    fostexDir = config.get('CategoryFolders', 'fostex-audio')
    marantzDir = config.get('CategoryFolders', 'marantz-audio')
    mdDir = config.get('CategoryFolders', 'audio')

    if last_dir == xdcamDir:
        return 'sony-xdcam'
    elif last_dir == dvDir:
        return 'video'
    elif last_dir == fostexDir:
        return 'fostex-audio'
    elif last_dir == marantzDir:
        return 'marantz-audio'
    elif last_dir == mdDir:
        return 'audio'
    else:
        print 'Path must terminate with one of the following directory names: '+xdcamDir+', '+dvDir+', '+fostexDir+', '+marantzDir+', '+mdDir
        print ltoUtil.get_script_name()+' script terminated.'
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
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
            
    elif media_file_count == 0:
        print 'No recognised media files were found in: '+path
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)

def session_device_check(config, session_id, device_code):
    if not ltoUtil.valid_chars(session_id):
        print 'Invalid characters used in session id.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    if not ltoUtil.valid_chars(device_code):
        print 'Invalid characters used in device_code.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
        
    session_exists_qry = 'exists(/session[@id="'+session_id+'"])'
    device_exists_qry = 'exists(//deviceCode[@id="'+device_code+'"])'
    media_exists_for_session_device_qry = 'exists(/session[@id="'+session_id+'"]//device[@code="'+device_code+'"]/*)'
    
    xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_transcript_url(config)+'/data', session_exists_qry)
    if not ltoUtil.get_parsed_xquery_value(xquery_result) == ['true']:
        print 'session id: '+session_id+' does not yet exist.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_transcript_url(config)+'/reference', device_exists_qry)
    if not ltoUtil.get_parsed_xquery_value(xquery_result) == ['true']:
        print 'device code: '+device_code+' does not exist.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_transcript_url(config)+'/data', media_exists_for_session_device_qry)   
    if ltoUtil.get_parsed_xquery_value(xquery_result) == ['true']:
        print 'At least one media item has already been associated with session: '+session_id+' and device: '+device_code
        print
        print 'To see the associated media items for this session open the following link in your browser:'
        print 'http://'+ltoUtil.get_host_port(config)+ltoUtil.get_transcript_url(config)+'/data?_query=/session[@id="'+session_id+'"]//mediaMetadata'
        print
        cont = raw_input('Are you sure you want to continue? [y/n]: ')
        if cont == 'y':
            return 
        else:
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)

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
    tb = ltoUtil.get_tar_build_dir(config)
    extn = string.lower(ltoUtil.get_file_extn(filepath))
    new_fp = tb+'/'+domain+'-'+media_id+'.'+extn
    return new_fp

def move_tar_files(config, session_id, device_code):
    tb = ltoUtil.get_tar_build_dir(config)
    archive_id = session_id+'-'+device_code
    tar = tb+'/'+archive_id+'.tar'
    xml = tb+'/'+archive_id+'.xml'
    dest = config.get('Dirs', 'tar_archive_dir')
    try: 
        print '\nMoving '+archive_id+'.tar to '+dest 
        ltoUtil.move(tar, dest)
        print '\nMoving '+archive_id+'.xml to '+dest 
        ltoUtil.move(xml, dest)
    except Exception, e:
        print '\nUnable to move archive files to: '+dest
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)

def create_referenced_items_file(config, session_id, device_code):
    tarMeta = open(os.path.join(ltoUtil.get_tar_build_dir(config), session_id+'-'+device_code+'-referenced-items.xml'),'w')
    params = urllib.urlencode({'sessionIds':session_id, 'deviceCodes':device_code})
    conn = httplib.HTTPConnection(ltoUtil.get_host_port(config))
    try:
        conn.request('GET', ltoUtil.get_transcript_url(config)+'/xquery/get-referenced-items.xql?'+params, None, {})
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
    conn = httplib.HTTPConnection(ltoUtil.get_host_port(config))
    try:
        conn.request('GET', ltoUtil.get_transcript_url(config)+'/xquery/get-next-media-id.xql?'+params, None, {})
        response = conn.getresponse()
        data = response.read()
        if '<exception>' in data:
            print ltoUtil.get_xquery_exception_msg(data)
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
        else:
            return data
    except httplib.HTTPException, e:
        print 'Unable to connect to database'
    else:
        conn.close()

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
    xquery_result = ltoUtil.exec_url_xquery(config, ltoUtil.get_transcript_url(config)+'/data', media_id_exists_for_domain_qry)
    if ltoUtil.get_parsed_xquery_value(xquery_result) == ['true']:
        return True
    else:
        return False

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
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
        #Insert hyphen if un-hyphenated
        id = alpha_part+'-'+str(num_part)
        if db_media_id_exists(domain, id, config):
            print 'The '+domain+' media id: '+id+' has already been used.'
            print ltoUtil.get_script_name()+' script terminated.'
            sys.exit(2)
    else:
        print 'Captured media filename: '+fn+' in wrong format.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    return id   

def get_new_media_id(session_id, domain, category, config, previous_id, filepath):
    if category == 'sony-xdcam':
        id = generate_new_id(session_id, domain, config, previous_id)
    elif category == 'video':
        id = get_id_from_filename(filepath, domain, config)
    elif category == 'fostex-audio':
        id = generate_new_id(session_id, domain, config, previous_id)
    elif category == 'marantz-audio':
        id = generate_new_id(session_id, domain, config, previous_id)
    elif category == 'audio':
        id = get_id_from_filename(filepath, domain, config)
    else:
        print 'Undefined media category: '+category
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    return id
        
def generate_db_media_xml_element(media_path, domain, category, media_id, config):
    if media_in_category(media_path, category, config):
        if category == 'sony-xdcam':
            mfile = open(media_path, 'r')
            num_bytes_mp4_xml_data = 1143
            mfile.seek(-num_bytes_mp4_xml_data, 2)
            mp4xml = mfile.read()
            timestamp = get_sonyxdcam_timestamp(mp4xml)
            original_id = get_original_id(media_path)
            duration = get_media_duration(media_path)
            auto_split = get_autosplit(media_path)
            attributes = {'timestamp':timestamp, 'originalId':original_id, 'duration':duration,'autoSplit':auto_split}    
        elif category == 'video':
            duration = get_media_duration(media_path)
            attributes = {'originalId':original_id, 'duration':duration}
        elif category == 'fostex-audio':
            mfile = open(media_path, 'r')
            num_bytes_bwf_xml_data = 10945
            mfile.seek(num_bytes_bwf_xml_data, 0)
            bwfxml = mfile.read(615)
            timestamp = get_fostexaudio_timestamp(bwfxml)
            original_id = get_original_id(media_path)
            duration = get_media_duration(media_path)
            attributes = {'timestamp':timestamp, 'originalId':original_id, 'duration':duration}
        elif category == 'marantz-audio':
            mfile = open(media_path, 'r')
            num_bytes_wf_str_data = 364
            mfile.seek(num_bytes_wf_str_data, 0)
            str = mfile.read(18)
            timestamp = get_marantzaudio_timestamp(str)
            original_id = get_original_id(media_path)
            duration = get_media_duration(media_path)
            attributes = {'timestamp':timestamp, 'originalId':original_id, 'duration':duration}
        elif category == 'audio':
            duration = get_media_duration(media_path)
            attributes = {'originalId':original_id,'duration':duration}
    else:
        original_id = get_original_id(media_path)
        attributes = {'originalId':original_id}
    return create_media_xml_element(domain, attributes, media_id)

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

def get_fostexaudio_timestamp(xml):
    start = xml.find('<SCENE>')+7
    end = xml.find('</SCENE>')
    ts = xml[start:end]
    year = ts[15:19]
    month_word = ts[12:15]
    day = ts[10:12]
    hr = ts[1:3]
    min = ts[4:6]
    sec = ts[7:9]
    months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
    month = '%02d' % (months.index(month_word) + 1)
    dt = year+'-'+month+'-'+day+'T'+hr+':'+min+':'+sec
    return dt 

def get_marantzaudio_timestamp(str):
    year = str[0:4]
    month = str[5:7]
    day = str[8:10]
    hr = str[10:12]
    min = str[13:15]
    sec = str[16:18]
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
    
    fn = ltoUtil.get_filename(new_filepath)
    path = ltoUtil.get_path(new_filepath)
    
    print 'Generating PAR2 files for '+fn+'\n'
    p = subprocess.Popen(par2_cmd +' create -r'+str(par2_redundancy)+' -m'+str(par2_memory)+' -n'+str(par2_numfiles)+' '+new_filepath, shell=True)
    sts = os.waitpid(p.pid, 0)
    par2files = []
    for f in os.listdir(path):
        if str(f).startswith(fn) and str(f).endswith('.par2'):
            par2files.append(f)
            
    par2filesstr = string.join(par2files, ' ')
    p = subprocess.Popen('tar -c --format='+ltoUtil.get_tar_format(config)+' -C '+path+' -f '+new_filepath+'.par2.tar '+par2filesstr, shell=True)
    sts = os.waitpid(p.pid, 0)
    for p in par2files:
        os.remove(os.path.join(path, p))
    
def generate_low_res(domain, filepath, dir):
    if (domain == 'video'):
        video_type = get_video_type(filepath)
        if video_type == 'DV_PAL' or video_type == 'DV_NTSC' or video_type == 'MPEG2_H-14':
            preview_size = '384x288'
        elif video_type == 'MPEG2_HL':
            preview_size = '512x288'
        preview_suff = 'h261_'+preview_size
        preview_file = filepath[0:-3]+preview_suff+'.mp4'
        fn = ltoUtil.get_filename(preview_file)
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

def db_add_media_xml(config, db_media_xml_doc, username, password):  
    deviceElement = db_media_xml_doc.getElementsByTagName('device')[0]
    session_id = deviceElement.getAttribute('sessionId')
    device_code = deviceElement.getAttribute('code')
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    authheader =  "Basic %s" % base64string
    headers = {'Authorization': authheader}
    conn = httplib.HTTPConnection(ltoUtil.get_host_port(config))
   
    if len(deviceElement.childNodes) == 0:
        print 'Internal Error: No session-media xml nodes generated.'
        print ltoUtil.get_script_name()+' script terminated.'
        sys.exit(2)
    
    for mediaElem in deviceElement.childNodes:
        if mediaElem.nodeType == xml.dom.Node.ELEMENT_NODE:
            element_xml = str(mediaElem.toxml())
            #Hack to put id as the first attribute
            element_xml = string.replace(element_xml, '_id="', 'id="')
            params = urllib.urlencode({'sessionId': session_id, 'deviceCode': device_code, 'mediaXML': element_xml})
            try:
                conn.request('GET', ltoUtil.get_transcript_url(config)+'/xquery/import-media-element.xql?'+params, None, headers)
                response = conn.getresponse()
                data = response.read()
                if '<exception>' in data:
                    print ltoUtil.get_xquery_exception_msg(data)
                    print ltoUtil.get_script_name()+' script terminated.'
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
    mediaElement.setAttribute('md5', ltoUtil.get_md5_hash(filepath))
    mediaElement.setAttribute('size', str(ltoUtil.get_filesize(filepath)))
    mediaElement.setAttribute('filename', ltoUtil.get_filename(filepath))
    doc.documentElement.appendChild(mediaElement)
    par2TarElement = doc.createElement('par2Tar')
    par2TarElement.setAttribute('md5', ltoUtil.get_md5_hash(filepath+'.par2.tar'))
    par2TarElement.setAttribute('size', str(ltoUtil.get_filesize(filepath+'.par2.tar')))
    par2TarElement.setAttribute('filename', ltoUtil.get_filename(filepath)+'.par2.tar')
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
    doc.documentElement.setAttribute('md5', ltoUtil.get_md5_hash(ltoUtil.get_tar_build_dir(config)+'/'+tar_name))
    doc.documentElement.setAttribute('size', str(ltoUtil.get_filesize(ltoUtil.get_tar_build_dir(config)+'/'+tar_name)))

def media_process_loop(domain, category, config, session_id, path, db_media_xml_doc, tar_xml_doc): 
    previous_id = None
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            if media_in_domain(file, domain, config):

                filepath = os.path.join(dirpath, file)
                media_id = get_new_media_id(session_id, domain, category, config, previous_id, filepath)
                db_media_xml_element = generate_db_media_xml_element(filepath, domain, category, media_id, config)
                append_db_media_xml_element(db_media_xml_doc, db_media_xml_element)
                
                new_filepath = get_new_filepath(config, domain, media_id, filepath)
                ltoUtil.copy_file(filepath, new_filepath)
                
                generate_par2_tar(config, new_filepath)
                proxy_media_dir = ltoUtil.get_proxy_media_dir(config)
                generate_low_res(domain, new_filepath, proxy_media_dir)
                append_tar_media_xml_element(tar_xml_doc, new_filepath, domain, media_id)
                previous_id = media_id
                    
                    
def create_tar_archive(config, session_id, device_code, tar_xml_doc):
    ref_file_name = session_id+'-'+device_code+'-referenced-items.xml'
    tar_name = session_id+'-'+device_code+'.tar'
    tar_path = ltoUtil.get_tar_build_dir(config)+'/'+tar_name
    block_size_bytes = int(config.get('Tape', 'block_size_bytes'))
    blocking_factor = block_size_bytes/512
    filelist = []
    for file in os.listdir(ltoUtil.get_tar_build_dir(config)):
        filelist.append(file)
    filelist.remove(ref_file_name)
    filelist.sort()   
    
    filelist_str = ref_file_name+' '+string.join(filelist, ' ')
    print '\nCreating tar archive: '+tar_path
    p = subprocess.Popen('tar -cvR -b '+str(blocking_factor)+' --format='+ltoUtil.get_tar_format(config)+' -C '+ltoUtil.get_tar_build_dir(config)+' -f '+tar_path+' '+filelist_str, shell=True, stdout=subprocess.PIPE)
    stdout_value = p.stdout.readlines()
    del stdout_value[0]
    for line in stdout_value:
        update_block_xml_attributes(tar_xml_doc, line, config)
       
    update_tar_xml_root_attributes(config, tar_xml_doc, tar_name)
    
    
def create_tar_xml_file(config, session_id, device_code, tar_xml_doc):
    
    xmlfile = open(ltoUtil.get_tar_build_dir(config)+'/'+session_id+'-'+device_code+'.xml', "w")
    pretty_doc = tar_xml_doc.toprettyxml()
    #Hack to put id attribute at the start
    pretty_doc = string.replace(pretty_doc, '_id="', 'id="')
    xmlfile.write(pretty_doc)
    xmlfile.close()
    
    
def write_media_xml_to_db(config, session_id, device_code, db_media_xml_doc):
    
    #Ask user for confirmation to write media xml to database
    update = raw_input('\nUpdate database with session-media metadata? [y/n]: ')
    xml_media_filename = session_id+'-'+device_code+'-media.xml' 
    xml_media_filepath = config.get('Dirs', 'tar_archive_dir')+'/'+xml_media_filename
    if update == 'y':
        username = raw_input('username: ')
        password = getpass.getpass('password: ')
        if db_add_media_xml(config, db_media_xml_doc, username, password):
            print '\nDatabase updated'
        else:
            print '\nFailed to update database'
            ltoUtil.write_xml(db_media_xml_doc, xml_media_filepath)
            print '\nMedia xml saved to '+xml_media_filepath
    else:
        ltoUtil.write_xml(db_media_xml_doc, xml_media_filepath)
        print '\nMedia xml saved to '+xml_media_filepath
       