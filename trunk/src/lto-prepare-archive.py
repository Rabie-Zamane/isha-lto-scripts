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
            
def generate_supp_tar(file, filelist):
    suppfilelist = string.join(filelist, ' ')
    os.system('star -c -b'+str(blocksize)+' artype='+archivetype+' '+suppfilelist+' > '+file+'.supplementary.tar')
    
def generate_preview(file):
    previewsuffix = 'h261_512x288'
    previewfilename = file[0:-3]+previewsuffix+'.mp4'
    os.system('ffmpeg -y -i '+file+' -pass 1 -vcodec libx264 -vpre ~/ffmpeg/ffpresets/libx264-fastfirstpass.ffpreset -s 512x288 -b 512k -bt 512k -threads 0 -f mp4 -an /dev/null && ffmpeg -y -i '+file+' -pass 2 -acodec libfaac -ab 128k -vcodec libx264 -vpre ~/ffmpeg/ffpresets/libx264-hq.ffpreset -s 512x288 -b 512k -bt 512k -threads 0 -f mp4 '+previewfilename)
    
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
    return "123"

def get_filesize(file):
    return os.path.getsize(file)
    
def db_import_media_xml(session, device, mediaxml):
    url = 'http://localhost:8080/exist/rest//db/ts4isha/xquery/import-media-element.xql?sessionId='+session+'&deviceId='+device+'&mediaXML='+mediaxml
    f = urllib2.urlopen(url)
    return f.read()
 
 
sessionid = sys.argv[1]
deviceid = sys.argv[2]
mp4s = []
#eventtypeid = sessionid[0:sessionid.find("-")]


for dirpath, dirnames, filenames in os.walk(os.getcwd()):
    for file in filenames:
        if file.endswith('.MP4'):
            mp4s.append(os.path.join(dirpath, file))
            mp4s.sort()


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

    generate_media_index_xml()

    
  



