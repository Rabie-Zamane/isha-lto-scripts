'''
Created on 14-Apr-2009

@author: kevala
'''

import os
import urllib
import urllib2
import xml.dom.minidom
import subprocess
import string
import md5sum2
import base64


def generate_par2_tar(cmd, r, m, n, file, b, artype):
    print 'Generating PAR2 files for '+file+'\n'
    p = subprocess.Popen(cmd +' create -r'+str(r)+' -m'+str(m)+' -n'+str(n)+' '+file, shell=True)
    sts = os.waitpid(p.pid, 0)
    par2files = []
    for f in os.listdir(os.getcwd()):
        if str(f).startswith(file) and str(f).endswith('.par2'):
            par2files.append(f)
            par2filesstr = string.join(par2files, ' ')
            p = subprocess.Popen('star -c -b'+str(b)+' artype='+artype+' '+par2filesstr+' > '+file+'.par2.tar', shell=True)
            sts = os.waitpid(p.pid, 0)
    for p2 in par2files:
        os.remove(p2)
            
def generate_supp_tar(file, filelist, b, artype):
    suppfilelist = string.join(filelist, ' ')
    p = subprocess.Popen('star -c -b'+str(b)+' artype='+artype+' '+suppfilelist+' > '+file+'.supplementary.tar', shell=True)
    sts = os.waitpid(p.pid, 0)
    for s in filelist:
        os.remove(s)
    
def generate_preview(file, dir):
    previewsuffix = 'h261_512x288'
    previewfilename = file[0:-3]+previewsuffix+'.mp4'
    p = subprocess.Popen('ffmpeg -y -i '+file+' -pass 1 -vcodec libx264 -vpre ~/ffmpeg/ffpresets/libx264-fastfirstpass.ffpreset -s 512x288 -b 512k -bt 512k -threads 0 -f mp4 -an /dev/null && ffmpeg -y -i '+file+' -pass 2 -acodec libfaac -ab 128k -vcodec libx264 -vpre ~/ffmpeg/ffpresets/libx264-hq.ffpreset -s 512x288 -b 512k -bt 512k -threads 0 -f mp4 '+dir+'/'+previewfilename, shell=True)
    sts = os.waitpid(p.pid, 0)
    #Cleanup
    os.remove('ffmpeg2pass-0.log')
    os.remove('x264_2pass.log')
    
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
           
def db_add_media_xml(sessionid, deviceid, mediasXmlDoc, username, password, host='localhost:8080'):
    for e in mediasXmlDoc.getElementsByTagName('video'):
        mediaXML = str(e.toxml())
        #Hack to put id as the first attribute
        mediaXML = string.replace(mediaXML, '_id="', 'id="')
        mediaXMLencoded = urllib.quote(mediaXML)
        url = 'http://'+host+'/exist/rest//db/ts4isha/xquery/import-media-element.xql?sessionId='+sessionid+'&deviceCode='+deviceid+'&mediaXML='+mediaXMLencoded
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
    return True

def db_get_next_media_id(session, domain, host='localhost:8080'):
    eventType = session[:session.find('-')]
    url = 'http://'+host+'/exist/rest//db/ts4isha/xquery/get-next-media-id.xql?domain='+domain+'&eventType='+eventType
    req = urllib2.Request(url)
    f = urllib2.urlopen(url)
    return f.read()

def generate_media_index_xml(doc, filename, domain, id):
    mediaElement = doc.createElement(domain)
    mediaElement.setAttribute('_id', id)
    mediaElement.setAttribute('md5', get_md5_hash(filename))
    mediaElement.setAttribute('size', str(get_filesize(filename)))
    doc.documentElement.appendChild(mediaElement)
    mediaElement.appendChild(generate_media_child_index_xml(doc, filename,'par2'))
    mediaElement.appendChild(generate_media_child_index_xml(doc, filename,'supplementary'))
    return mediaElement
 
def generate_media_child_index_xml(doc, filename, type):
    childElement = doc.createElement(type+'Tar')
    childElement.setAttribute('md5', get_md5_hash(filename+'.'+type+'.tar'))
    return childElement

def create_tar_xml(session, device):
    doc = xml.dom.minidom.Document()
    tarElement = doc.createElement('tar')
    doc.appendChild(tarElement)
    tarElement.setAttribute('sessionId', session)
    tarElement.setAttribute('deviceCode', device)
    return doc

def create_media_metadata_xml(sessionid, deviceid):
    doc = xml.dom.minidom.Document()
    root = doc.createElement('mediaMetadata')
    doc.appendChild(root)
    devElement = doc.createElement('device')
    root.appendChild(devElement)
    devElement.setAttribute('code', deviceid)
    devElement.setAttribute('sessionId', sessionid)
    return doc

def append_media_element(doc, id, timestamp, duration, originalId, autosplit):
    mediaElement = doc.createElement('video')
    deviceElements = doc.getElementsByTagName('device')
    deviceElement = deviceElements[0]
    deviceElement.appendChild(mediaElement)
    mediaElement.setAttribute('autoSplit', autosplit)
    mediaElement.setAttribute('originalId', originalId)
    mediaElement.setAttribute('duration', duration)
    mediaElement.setAttribute('timestamp', timestamp)
    mediaElement.setAttribute('_id', id)

def create_tar_event_metadata_file(filename, sid, host='localhost:8080'):
    tarMeta = open(filename,'w')
    url = 'http://'+host+'/exist/rest//db/ts4isha/xquery/get-referenced-items.xql?sessionIds='+sid
    f = urllib2.urlopen(url)
    tarMeta.writelines(f.readlines())
    tarMeta.close()

def update_block_xml_attributes(doc, domain, filename, offset):
    id = filename[filename.find('-')+1:filename.find('.')]
    mediaElems = doc.getElementsByTagName(domain)
    for e in mediaElems:
        atts = e.attributes
        for attName in atts.keys():
            attNode = atts.get(attName)
            attValue = attNode.nodeValue
            if attName == '_id' and attValue == id:
                if filename.endswith('.mp4'):
                    e.setAttribute('blockOffset', offset)
                elif filename.endswith('par2.tar'):
                    par2Elems = e.getElementsByTagName('par2Tar')
                    par2Elem = par2Elems[0]
                    par2Elem.setAttribute('blockOffset', offset)
                elif filename.endswith('supplementary.tar'):
                    suppElems = e.getElementsByTagName('supplementaryTar')
                    suppElem = suppElems[0]
                    suppElem.setAttribute('blockOffset', offset)
                    
def update_tar_xml_attributes(doc, filename):                    
    doc.documentElement.setAttribute('md5', get_md5_hash(filename))
    doc.documentElement.setAttribute('size', str(get_filesize(filename)))
    
def write_xml(xmldoc,file):
    f = open(file, "w")
    f.write(xmldoc.toprettyxml())
    f.close()
