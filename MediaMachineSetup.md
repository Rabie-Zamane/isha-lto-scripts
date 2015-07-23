# Introduction #

This machine will receive all media files and perform the first stage of the LTO processing on them. This includes manually checking/viewing the media files (using the winxp-xdcam-clipbrowser virtual machine), creating low resolution preview versions, creating PAR2 error correction files, and building session-device tar archive files ready to be written to tape.

The tar files will then be transferred to the server via FTP

## Hardware Setup ##

The machine we are using for the "Media Machine" is a Lenovo PC...

## Software Setup ##

We have installed CentOSPlus as our OS.

### Python LTO Scripts ###

On the Media Machine we will only be running the first of the lto scripts (lto-tar).

### eXist Database setup ###

We need to do the following things to set up the eXist database to be able to store the lto tape index files.

  * Create a top-level collection called "lto4isha" (at the same level as ts4isha), with corresponding "data", and "xquery" sub collections.

  * Add the .xql files from the lto4isha distribution to the xquery collection, (get-file-lto-vector.xql, get-session-full-name.xql, import-tape-element.xql)

### Python setup ###

The version of python included with CentOS 5.3 (v2.4.3) is too old and doesn't have some of the libraries we need. So we need to download the python source for the latest stable release (v2.6.2) from [here](http://www.python.org/download/releases/2.6.2/), and build it oureselves.

### Installing par2 ###

### Installing ffmpeg ###

Since the version of ffmpeg available in the rpmforge repository is not recent enough to handle H.264 video encoding properly, we need to build ffmpeg from source, with the necessary codec libraries. [This page](http://thenitai.com/2009/02/24/installing-ffmpeg-on-centosredhat-5x-successfully/) explains how to do this.

Note that we first need to install the development tools package group:

  1. yum groupinstall 'Development Tools'

We also need to install the 'git' package to access the most recent version of the x264 library from their git repository.


### JW Player Embedding ###

Note that the playerReady() function does not get called in Linux unless the flashvar id variable is set. See [here](http://www.longtailvideo.com/support/forum/JavaScript-Interaction/17227/Firefox-3-playerReady-never-gets-called#msg116643) for details.