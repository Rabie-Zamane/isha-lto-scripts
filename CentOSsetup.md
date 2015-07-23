# Introduction #

This document contains the instructions on how to install and configure the CentOS Operating System, installing the necessary software and hardware, to be able to perform the LTO backups, and to run the TranscriptStudio application.


## Why CentOS ##

We have chosen to use the Linux OS because it is generally considered to offer greater stability, security when compared to Microsoft Windows. We also wanted to use an open source model for our data backup architecture, to avoid storing our data in proprietary formats, and therefore avoid the risk of being unable to access it in the future due to software version incompatibilities or discontinuities. For this reason Linux was the natural choice.

The reason why we have chosen the CentOS distribution of Linux is primarily because we are using an HP Tape Drive (Storageworks Ultrium 920 External SCSI) together with an HP SCSI HBA Card [(SC11Xe PCIe Ultra320)](http://h20000.www2.hp.com/bizsupport/TechSupport/SoftwareIndex.jsp?lang=en&cc=us&prodNameId=3191202&prodTypeId=329290&prodSeriesId=3191201&swLang=8&taskId=135&swEnvOID=4006), both of which are only supported, (and have drivers/firmware available) for the enterprise versions of either RHEL or SUSE.

CentOS aims to be, as far as possible, a "binary clone" of RHEL (using the freely available source code under the GPL license), but with the advantage of being free. Using an "enterprise" distribution also means that we are less at risk from bugs introduced by having the "latest and greatest" updates, which might be the case with using an OS like Ubuntu for example.


## Installing CentOS ##

During the install enable the Firewall

We need to install the latest version of CentOS (with the CentOS Plus repository enabled, and with the CentOSPlus kernel). The CentOS Plus repository contains extra packages which are not in the official RedHat distribution - so it means that is "unsupported". However, we require the firewire IE1394 support, which is only enabled in the CentOS Plus kernel)

We also need to enable the 3rd part repository RPMForge in order to get the gparted partitioning package. See [here](http://wiki.centos.org/AdditionalResources/Repositories/RPMForge/) for guidelines on how to do this

## Hardware Installation ##

We are using the following hardware:
  * IBM System x3400 (7973) Server
  * HP Storageworks Ultrium 920 LTO-3 External Scsi Tape Drive
  * HP SC11Xe Ultra 320 PCIe HBA card (OEM version of LSI card)
  * 2 Western Digital Velociraptor 10000rpm 300GB Sata Hard Disks


### Installing the HP SC11Xe HBA card ###

We used the LSI Logic driver, available from [here](http://www.lsi.com/storage_home/products_home/host_bus_adapters/scsi_hbas/lsi20320ie/). We installed the dkms rpm and then the mptlinux-dkms rpm.

(Note: The official HP driver for this card is available [here](http://h20000.www2.hp.com/bizsupport/TechSupport/SoftwareDescription.jsp?lang=en&cc=uk&prodTypeId=329290&prodSeriesId=3191201&swItem=MTX-0cfb66c3937346129f6ce9ed13&prodNameId=3191202&swEnvOID=4006&swLang=8&taskId=135&mode=4&idx=2), but we found that it gave sub-optimal performance compared to the LSI driver, as well as restricting us to a particular kernel version. With the HP driver the tape drive was able to write around 95% capacity of the tape - 375GB out of 391GB, whereas the LSI driver was able to write close to 100% capacity - both at around 55MBps.

If for any strange reason we need to use the HP driver, a couple of things (hacks) need to be done to make the installation work properly.

  1. Change the value stored in the file /etc/redhat-release from "CentOS release 5.3 (Final)" to "Red Hat Enterprise Linux Server release 5 (Tikanga)". If you don't do this, then the the installation will fail with a message saying that you don't have the correct distribution.

  1. Prevent mkinitrd from requiring the dm-mem-cache module. This can be accomplished by executing the following commands as root:

  1. echo "DMRAID=no" > /etc/sysconfig/mkinitrd/noraid
  1. chmod 755 /etc/sysconfig/mkinitrd/noraid

More information on what this means can be found [here](http://kbase.redhat.com/faq/docs/DOC-16528)

### Rescanning the SCSI bus ###

If the server is powered on before the tape drive, then the tape drive will not be detected automatically after it is switched on. To get the server to detect the tape drive without having to restart the server you can rescan the scsi bus, by entering the following command as root:

  * echo "- - -" > /sys/class/scsi\_host/host?/scan

(replacing "?" with the number of the host - e.g. 0, 1, 2, 3)

### RAID disk setup ###

mdadm -C --verbose --raid-devices=2 --chunk=256 --level=raid0 /dev/sdb1 /dev/sdd1

### Enabling Firewire ###

In order to facilitate receiving and offloading large amounts of data from external firewire drives, we need to enable firewire support in the linux kernel.

By default RedHat/CentOS does not have firewire support enabled in the kernel. This means that either one must recompile the kernel enabling the appropriate kernel modules - or more easily - upgrade to the CentOSPlus kernel, which has firewire support enabled automatically. (We have chosen the latter - for the sake of simplicity).

See [this link](http://wiki.centos.org/AdditionalResources/Repositories/CentOSPlus) for details on how to set up the yum configuration files properl

NOTE: If using the HP HBA Card driver this would cause a problem since the HP HBA card requires us to have one of a specified list of kernel versions  - of which the CentOSPlus kernel is not one of.

### Enabling NTFS Read/Write Support ###

See [this link](http://wiki.centos.org/TipsAndTricks/NTFS#note_for_cplus) for more info

### Resizing Ext3 partitions ###

See [this link](http://wiki.centos.org/TipsAndTricks/ResizeExt3) for more info

### Setting up a static IP address ###

See [here](http://www.thewebmasterscafe.net/webhosting/how-to-configure-static-ip-address-on-centos-linux.html) to find out how to configure a static IP address, and see [here](http://www.more.net/technical/netserv/tcpip/viewip.html) to see how to find out the values of the needed parameters (subnet-mask, dns, defalt-gateway)

### Transferring files between machines (FTP) ###

See [here](http://www.fedoraforum.org/forum/showthread.php?t=177674) for more info
and [here](http://www.cyberciti.biz/faq/ftp-connection-refused-error-solution-to-problem/) for ftp info.

After testing different methods of transferring files between the two machines - we found that FTP was the fastest by a large margin (85MBps compared to 30MBps for scp). This allows us to transfer around 100GB of data between the machines in approx 20mins.

We need to install vsftpd on the server (and also on the media machine if we want to send files to it from the server). On the media machine we installed gftp to provide a GUI for the ftp command.

Note that we must allow FTP access in the Security and Firewall settings in order to be able to connect.

To start vsftpd as a service on the server, first edit the file /etc/init.d/vsftpd and change the line "# chkconfig: - 60 50" to "# chkconfig: 2345 60 50" (i.e. replace the hyphen by the numbers 2345). Then execute the following commands as root:

  * /sbin/chkconfig --del vsftpd (to delete the existing service configuration)
  * /sbin/chkconfig --add vsftpd

A handy alternative to using an FTP client is to do the following:

  * On the menu, go to Places -> Connect to Server...
  * Select ServiceType as FTP (with login) , and enter the the ip address of the server and optionally other info.

This will put an icon on the desktop which can be used to access the remote system.

### Database Backups with Cron ###

We want to run a nightly backup of the database

edit /etc/crontab
edit /etc/cron.daily/exist.cron ...

## Software Installation ##

### Installing Java ###

Get the latest version of the Java jdk from [Sun's website](http://java.sun.com/javase/downloads/index.jsp). Move the binary executable to /opt, make the file executable (by typing chmod u+x filename) and execute it as root.

Instructions on how to perform the installation can be found [here](http://www.cyberciti.biz/faq/linux-unix-set-java_home-path-variable/). (See the comments by Mustafa Buljubasic)

Ensure that you use the 'alternatives' command to use sun's version of java.

Set the $JAVA\_HOME and $PATH system environment variables by creating the file /etc/profile.d/jdk.sh with the following lines:

  * export JAVA\_HOME=/opt/jdk1.6.0\_13 (or whatever version of Java you have)
  * export PATH=$JAVA\_HOME/bin:$PATH

### Installing eXist ###

Get the latest stable version of the eXist xml database from [here](http://exist.sourceforge.net/download.html), and copy it to /opt

Install it by typing the following command as root

  * java -jar eXist-{version}.jar

Note: Ensure that you specify a non-empty password for the admin user, else this may cause problems later on.

Set the $EXIST\_HOME system environment variable by creating the file /etc/profile.d/exist.sh with the following lines:

  * export EXIST\_HOME=/opt/exist

To configure eXist to start as a service

See [here](http://exist.sourceforge.net/quickstart.html#sect9)

See [this link](http://www.centos.org/docs/5/html/Deployment_Guide-en-US/ch-services.html) to learn more about services in RedHat

Create the following symlink

  * ln -s $EXIST\_HOME/tools/wrapper/bin/exist.sh /etc/init.d/exist

Then edit the file so that it contains the following lines near the beginning of the file:

# chkconfig: 2345 20 80

# description: Starts and stops eXist xml database

This says that the script should be started in levels 2,  3,  4,and 5, that its start priority should be 20, and that its stop priority should be 80.

Now execute the following command to add exist as a service:

  * chkconfig --add exist


### Bypassing the Firewall ###

In order for other machines on the network to access the exist database we must configure the firewall to allow access to port 8080 (the default port which exist uses). To do this, go to System -> Administration -> Security Level and Firewall, and under "Other Ports" add 8080 (tcp).


### Installing the Flash Player plugin ###

You can get the latest Flash Player plugin from [here](http://get.adobe.com/flashplayer/), and select the YUM download option (and running the file). This will create an adobe yum repository file in /etc/yum.repos.d. Now the plugin can be installed by executing:

  * yum install flash-plugin

### Installing ts4isha ###

After installing, point your web browser at http://localhost:8080/exist/ts4isha/TranscriptStudio.swf to access the Transcript Studio application. (Note that you must have already installed the adobe flash-plugin for this to work).

## General Hints ##

This section contains some general information about how to perform some of the commonly used tasks in CentOS

### Package Management with YUM ###

su -c 'yum install tsclient' (Installs tsclient)
su -c 'yum update tsclient' (Updates tsclient to the latest version)
su -c 'yum remove tsclient' (Removes tsclient from the system)
su -c 'yum list tsclient' (Searches for package named tsclient)
su -c 'yum list tsc\**' (Search using wildcard)**

### Required Packages ###

  * ImageMagick
  * subversion
  * ffmpeg


Add your content here.  Format your content with:
  * Text in **bold** or _italic_
  * Headings, paragraphs, and lists
  * Automatic links to other wiki pages