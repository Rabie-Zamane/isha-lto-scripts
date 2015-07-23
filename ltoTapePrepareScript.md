# Introduction #

This script performs the following functions:

  * Recalculates all file "block" offset values depending on the order the archives will be written to tape, and generates a tape.xml file from all the pre-prepared "tar" fragments (updating the block attributes accordingly). Also calculates and updates the tar file position/block attributes. Adds the top-level index timestamp attribute.

# Details #

To run this script, all the pre-prepared archives+xml files must be placed in their own folders inside the "/lto-stage/tape/tape-id" directory (where tape-id ="1","2" etc...). Each archive, and its corresponding xml file must be named session-id-device-id (e.g. n65-1-v1), and stored in a directory of the same name.

The script is run within a tape-id directory, and performs the following steps:

Step 1: Check that the total filesize of all the archives is <= 370GB

Step 2: Generate the full tape.xml file, by looping through the archive files and adding each tar element, updating the "position" and "block" attribute values on the way.

Step 3: Pass the tape.xml to the database via an XQuery, and receive a tape-id in return (e.g."27"). Add this id to the tape.xml and write to file.