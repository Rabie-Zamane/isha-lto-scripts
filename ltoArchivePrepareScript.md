# Introduction #

This script performs the following functions (for each session-device folder):
  * Updates xml database with new media ids and selected additional media metadata
  * Creates PAR2 error correction files
  * Creates tar files (on staging disk)
  * Creates session-device "tar" xml element (includes calculating md5 hashes and block offsets for each file). This will be the tar element part of the main lto index xml file.
  * Creates preview video files


# Details #

Step by step script functions

Note: As a first step, the user is expected to have created the necessary event/sessions in the transcript studio application and made a note of the session-ids.

The script is called with 2 mandatory arguments: (-s session-id, -d device-id), and optional args: (-i start-index -h hostname)

The script must be called in a directory containing either a single "BPAV" folder (new videos), or a collection of .mov files (old videos). The script will perform different routines based on which it finds.

## New Video routine ##

Connect to xml db and issue xquery to generate the referenced-items.xml file (containing event/session/device metadata for the archive).

Connect to the xml db to retrieve the next available id for the event-type (as specified in the session-id)

The following steps will be performed for each MP4 file within the BPAV file:

Step 1: Parse some additional metadata from the "raw" sony xml file, and store it as in-memory xml fragment

Step 2: Copy the MP4 file to the current dir and rename it with a new id (includes 'domain' UUID prefix) (e.g. video-p-123.mp4)

Step 3: Generate the PAR2 files and combine them into n-1234.par2.tar file

Step 4: Create a n-1234.supplementary.tar file containing the "raw" sony xdcam xml file (not renamed)

Step 5: Generate the low resolution preview file using ffmpeg (store in a separate folder)

Step 6: Create a "media" xml element for the file (includes calculating the md5sum for the mp4 file and the par2 and supplementary files), and append to other media elements

Now - use "star" to create a "pax" archive of the referenced-items.xml, and all the .mp4 files par2.tar and supplementary.tar files. (Use star with the -v and -block-number options set, and capture the block offsets of each file from the stdout). Update the xml element with the block offset values.

Calculate the filesize and md5 hash for the whole tar archive, and update the xml.

Create the index-tar xml element from all the previously created media elements (leaving the tar element attributes "position" and "block" empty at this stage - since these can only be known when all the tar archives to be archived to a single tape are viewed together in the correct order). Write this xml file to disk (and give it the same name as the archive file (e.g. p-23-1-cam-1.tar p-23-1-cam-1.xml).

Ask user whether he wishes to update the db with the media xml metadata (calculated in Step 1). If user agrees, connect to db and update session.xml file. If not, write file to disk with the name: p-23-1-cam-1-media.xml (Later the user can update the db via the XQuery app)