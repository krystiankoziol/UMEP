# -*- coding: utf-8 -*-

# Resource object code
#
# Created: ti 29. sep 17:30:38 2015
#      by: The Resource Compiler for PyQt (Qt v4.8.5)
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore

qt_resource_data = "\
\x00\x00\x01\x2d\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x17\x00\x00\x00\x18\x08\x02\x00\x00\x00\x9e\x1e\xf1\x22\
\x00\x00\x00\x06\x74\x52\x4e\x53\x00\xff\x00\xff\x00\xff\x37\x58\
\x1b\x7d\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\
\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\xcd\x49\x44\x41\x54\x78\
\x9c\xa5\x94\xdd\x12\x85\x20\x08\x84\xa5\xf1\xbd\x19\x9f\x9c\x2e\
\x38\x43\x1b\x7f\xe9\x1c\xae\x48\xdd\xcf\xa5\x20\x12\x91\xb1\x17\
\x6b\xad\x31\x06\x33\xc7\xad\xeb\x7f\xc4\x01\xa5\xbf\x60\x9e\x0a\
\x34\x31\x53\xba\x72\x40\x41\xa5\xe1\x74\xbd\xab\xc8\x9d\x46\x99\
\x11\x35\x29\x29\xa6\x6f\x58\x96\x27\x15\x55\xc5\x37\xf1\xf2\x62\
\xd7\xa2\x67\xc3\x35\xac\xc7\x4b\xb4\xb0\x69\xc4\x7b\xb1\x3b\xf1\
\xa5\x44\x6b\x9d\x97\x0a\xd4\xeb\x13\x2f\xc8\x52\xf1\x0e\x22\xf1\
\x52\x85\x5a\x8b\xd3\x94\xf4\x6e\x35\x72\xb8\x1e\xdb\x87\x99\x27\
\x3e\xa0\xa6\x42\xb8\x93\x9a\x53\xf5\x7f\xc1\xb7\xfb\xd9\xbb\x24\
\x22\x44\xe4\x4e\x20\x3a\x2d\xd3\x2d\x5e\x4e\x53\x45\x9c\x63\xdc\
\x9d\x76\x79\x74\x14\x35\x55\x1f\xff\xfa\xa5\x41\x8c\xf7\x7c\xa5\
\x5e\x2e\x44\xa4\xa5\x59\x07\x2a\x2b\xed\xc3\xc7\x82\x21\x88\xbe\
\x3f\x9c\x73\xd4\xb9\xd8\x8f\x1b\xf0\xf6\xa3\xbe\x83\xec\x5d\x42\
\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82\
"

qt_resource_name = "\
\x00\x07\
\x07\x3b\xe0\xb3\
\x00\x70\
\x00\x6c\x00\x75\x00\x67\x00\x69\x00\x6e\x00\x73\
\x00\x0f\
\x09\x63\xc5\x9d\
\x00\x49\
\x00\x6d\x00\x61\x00\x67\x00\x65\x00\x4d\x00\x6f\x00\x72\x00\x70\x00\x68\x00\x50\x00\x61\x00\x72\x00\x61\x00\x6d\
\x00\x12\
\x0e\xbe\x78\x07\
\x00\x49\
\x00\x6d\x00\x61\x00\x67\x00\x65\x00\x4d\x00\x6f\x00\x72\x00\x70\x00\x68\x00\x49\x00\x63\x00\x6f\x00\x6e\x00\x2e\x00\x70\x00\x6e\
\x00\x67\
"

qt_resource_struct = "\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\
\x00\x00\x00\x14\x00\x02\x00\x00\x00\x01\x00\x00\x00\x03\
\x00\x00\x00\x38\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()
