'''
Created on 12-Apr-2009

@author: kevala
'''
#!/usr/bin/python

import distutils.file_util
import urllib
import urllib2
import os
import sys
import string
import md5sum2
import xml.dom.minidom
import base64

lto_home = '/lto-stage'
lto_previews = lto_home+'/h261'

blocksize = 128
par2multicpu = '/usr/bin/par2-multicpu/par2'
par2redundancy = 5
par2numfiles = 1
par2memory = 1000
archivetype = 'pax'

def generate_par2_tar(file):
    print 'Generating PAR2 files for '+file+'\n'
    os.system(par2multicpu +' create -r'+str(par2redundancy)+' -m'+str(par2memory)+' -n'+str(par2numfiles)+' '+file)
    par2files = []
    for f in os.listdir(os.getcwd()):
        if str(f).startswith(file) and str(f).endswith('.par2'):
            par2files.append(f)
            par2filesstr = string.join(par2files, ' ')
            os.system('star -c -b'+str(blocksize)+' artype='+archivetype+' '+par2filesstr+' > '+file+'.par2.tar')
    for p2 in par2files:
        os.remove(p2)
            
def generate_supp_tar(file, filelist):
    suppfilelist = string.join(filelist, ' ')
    os.system('star -c -b'+str(blocksize)+' artype='+archivetype+' '+suppfilelist+' > '+file+'.supplementary.tar')
    for s in filelist:
        os.remove(s)
    
def generate_preview(file):
    previewsuffix = 'h261_512x288'
    previewfilename = file[0:-3]+previewsuffix+'.mp4'
    os.system('ffmpeg -y -i '+file+' -pass 1 -vcodec libx264 -vpre ~/ffmpeg/ffpresets/libx264-fastfirstpass.ffpreset -s 512x288 -b 512k -bt 512k -threads 0 -f mp4 -an /dev/null && ffmpeg -y -i '+file+' -pass 2 -acodec libfaac -ab 128k -vcodec libx264 -vpre ~/ffmpeg/ffpresets/libx264-hq.ffpreset -s 512x288 -b 512k -bt 512k -threads 0 -f mp4 '+lto_previews+'/'+previewfilename)
    
def get_timestamp(xmlfile) :
    xmlfile.seek(0)
    for line in xmlfile:
        if 'CreationDate' in line:
            ts = line[line.find('"')+1:line.rfind('"')-6]
            return ts

def get_originalid(xmlfile):
    return xmlfile[xmlfile.rfind('/')+1:-7]

def get_duration(xmlfile):
    xmlfile.seek(0)
    for line in xmlfile:
        if 'Duration' in line:
            frs = line[line.find('"')+1:line.rfind('"')]
        if 'tcFps' in line:
            fps = line[line.find('"')+1:line.find('"')+3]
    totalsecsfl = float(frs)/int(fps)
    totalsecs = int(totalsecsfl)
    hrs = totalsecs/3600
    mins = (totalsecs%3600)/60
    secs = (totalsecs%3600)%60
    msecs = round(totalsecsfl - totalsecs, 2)*100
    return "%02d:%02d:%02d:%02d" % (hrs,  mins,  secs,  msecs) 

def get_autosplit(file1,  file2):
    if file1 == file2:
        return "false"
    else:
        suff1 = file1[-9:-7]
        suff2 = file2[-9:-7]
        if int(suff1) < int(suff2):
            return "true"
        else:
            return "false"
        
def get_md5_hash(file):
    return md5sum2.sum(file)

def get_filesize(file):
    return os.path.getsize(file)
    
def db_import_media_xml(session, device, mediaxml):
    username='admin'
    password='admin'
    url = 'http://localhost:8080/exist/rest//db/ts4isha/xquery/import-media-element.xql?sessionId='+session+'&deviceId='+device+'&mediaXML='+mediaxml
    req = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    authheader =  "Basic %s" % base64string
    req.add_header("Authorization", authheader)
    try:
        handle = urllib2.urlopen(req)
        print handle.read()
        return handle.read()
    except IOError, e:
        if hasattr(e, 'code'):
            if e.code != 401:
                print 'We got another error'
                print e.code
            else:
                print e.headers
                print e.headers['www-authenticate']
    
      




def db_get_event_metadata(session):
    url = 'http://localhost:8080/exist/rest/db/ts4isha/xquery/get-event-session-metadata.xql?sessionIds='+sessionid
    f = urllib2.urlopen(url)
    return f.read()

def generate_media_index_xml(filename, domain, id):
    doc = xml.dom.minidom.Document()
    mediaElement = doc.createElement(domain)
    doc.appendChild(mediaElement)
    mediaElement.setAttribute('id', id)
    mediaElement.setAttribute('md5', get_md5_hash(filename))
    mediaElement.setAttribute('size', str(get_filesize(newfilename)))
    
    mediaElement.appendChild(generate_media_child_index_xml(filename,'par2'))
    mediaElement.appendChild(generate_media_child_index_xml(filename,'supplementary'))
    return mediaElement
 
def generate_media_child_index_xml(filename, type):
    doc = xml.dom.minidom.Document()
    childElement = doc.createElement(type+'Tar')
    doc.appendChild(childElement)
    childElement.setAttribute('md5', get_md5_hash(filename+'.'+type+'.tar'))
    return childElement

def create_tar_xml(session, device):
    doc = xml.dom.minidom.Document()
    tarElement = doc.createElement('tar')
    doc.appendChild(tarElement)
    tarElement.setAttribute('sessionId', session)
    tarElement.setAttribute('deviceId', device)
    return tarElement

 
sessionid = sys.argv[1]
deviceid = sys.argv[2]
mp4s = []

print db_get_event_metadata(sessionid)


for dirpath, dirnames, filenames in os.walk(os.getcwd()):
    for file in filenames:
        if file.endswith('.MP4'):
            mp4s.append(os.path.join(dirpath, file))
            mp4s.sort()

tarXmlElement = create_tar_xml(sessionid, deviceid)

for index, mp4 in enumerate(mp4s):
    
    rawxml = mp4[0:-4]+'M01.XML'
    if index < len(mp4s)-1:
        nextrawxml = mp4s[index+1][0:-4]+'M01.XML'
    else:
        nextrawxml = rawxml
        
    xfile = open(rawxml)
    
    timestamp = get_timestamp(xfile)
    originalid = get_originalid(rawxml)
    duration = get_duration(xfile)
    autosplit = get_autosplit(rawxml, nextrawxml)
    xfile.close()
     
    #Update the database with the media metadata
    mediaxml = urllib.quote('<video timestamp="'+timestamp+'" duration="'+duration+'" previousIds="'+originalid+'" autoSplit="'+autosplit+'" />')
    newmediaid = db_import_media_xml(sessionid, deviceid, mediaxml)
    
    newfilename = 'video-'+newmediaid+'.mp4'
    distutils.file_util.copy_file(mp4, os.path.join(os.getcwd(), newfilename))
    
    generate_par2_tar(newfilename)
    
    distutils.file_util.copy_file(rawxml, os.getcwd())
    rawxmlname = rawxml[str(rawxml).rfind('/')+1:len(str(rawxml))]
    
    suppfiles = [rawxmlname]
    generate_supp_tar(newfilename, suppfiles)
    
    generate_preview(newfilename)
    
    mediaXmlElement = generate_media_index_xml(newfilename, 'video', newmediaid)
    tarXmlElement.appendChild(mediaXmlElement)
    

#print tarXmlElement.toprettyxml()
#Create the main archive

#for file in os.listdir(os.getcwd()):
#    if file.endswith('.mp4') or file.endswith('.tar'):
        
        


