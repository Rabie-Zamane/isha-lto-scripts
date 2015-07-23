## Xml Index File format ##

The format of the xml index file stored at the start of each tape




&lt;index id="1234" timestamp="2009-10-29T17:23:11"&gt;


> 

&lt;tar session-id="n162-1" device-id="v1" position="2" block="2983728" md5="9dsjdgeb3.."&gt;


> > 

&lt;video id="n1271" block="2983734" md5="edh47..." size="23292782"&gt;


> > > 

&lt;supplementary-tar block="21542772" md5="7dhd743679..." /&gt;



> > 

&lt;/video&gt;


> > ...
> > ...

> 

&lt;/tar&gt;


> ...
> ...


&lt;/index&gt;



Here, the session-id and device-id attributes on the tar element are optional. Later, for other types of media (e.g. photos) we may decide to group by something other than session-device (e.g. day/month), in which case we would use an alternative attribute (e.g. day-id).

Note: md5 hash is calculated at the tar level to speed up the tape verification process. (We only need to verify the hashes of the tars to be assured that the data is ok). If there is a checksum mismatch we can then examine the md5 hashes of the individual media files one by one.

## Data structure on tape ##

The tape will consist of a set of tar archives, each corresponding to a session-device (initially). The total filesize of all the archives must not exceed 370GB.

Each archive will consist of:

  * metadata.xml (Event/session metadata extracted from the database - stored on the tape for redundancy)
  * All the .mp4 or .mov video files for that session-device
  * For each video file - a "supplementary" tar archive, which can contain any additional files relating to the video file. For example, our xdcam video camera produces an xml file containing extra metadata about each video clip shot. In particular we will store PAR2 error correction files in this tar file, which can be used to repair the original file in case any corruption occurs.