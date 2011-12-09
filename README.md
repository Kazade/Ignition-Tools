# IGNITION TOOLS

## What is this?

This repo contains a set of tools I've developed to rip and convert resources from the abandonware game Ignition.

## pic2tga

Ignition stores many images in a custom format with a .PIC extension, this little app converts them to TGA format.

### Build

The tool depends on boost_program_options and the SOIL image library. You can build the app by running the following command:

g++ -Wall -std=c++0x pic2tga.cpp -o pic2tga -lboost_program_options -lSOIL
