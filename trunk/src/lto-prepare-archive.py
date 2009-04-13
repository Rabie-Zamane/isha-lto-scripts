'''
Created on 12-Apr-2009

@author: kevala
'''
#!/usr/bin/python

import distutils.file_util
import urllib2
import os
import sys

def get_timestamp (xmlfile) :
    xmlfile.seek(0)
    for line in xmlfile:
        if 'CreationDate' in line:
            ts = line[line.find('"')+1:line.rfind('"')-6]
            return ts

def get_originalid (xmlfile):
    return xmlfile[xmlfile.rfind('/')+1:-7]

def get_duration (xmlfile):
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

def get_autosplit (file1,  file2):
    if file1 == file2:
        return "false"
    else:
        suff1 = file1[-9:-7]
        suff2 = file2[-9:-7]
        if int(suff1) < int(suff2):
            return "true"
        else:
            return "false"
 
 
sessionid = sys.argv[1]
deviceid = sys.argv[2]
mp4s = []
eventtypeid = sessionid[0:sessionid.find("-")]


f = urllib2.urlopen('http://localhost:8080/exist/rest//db/ts4isha/xquery/get-last-id.xql?tagName=video&prefix='+eventtypeid)
print f.read()



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
    
    #mediametadataxml = '<video id="'+mediaid+'" timestamp="'+timestamp+'" duration="'+duration+'" previousIds="'+originalid+'" autoSplit="'+autosplit+'" />'
    
    print timestamp
    print originalid
    print duration
    print autosplit
    
    xfile.close()

    distutils.file_util.copy_file(mp4, os.path.join(os.getcwd(), 'video-'+eventtypeid+'-'+originalid[4:8]+'.mp4'))


    
  



