# KVM-based Discoverable Cloudlet (KD-Cloudlet)
# Copyright (c) 2015 Carnegie Mellon University.
# All Rights Reserved.
#
# THIS SOFTWARE IS PROVIDED "AS IS," WITH NO WARRANTIES WHATSOEVER. CARNEGIE MELLON UNIVERSITY EXPRESSLY DISCLAIMS TO THE FULLEST EXTENT PERMITTEDBY LAW ALL EXPRESS, IMPLIED, AND STATUTORY WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT OF PROPRIETARY RIGHTS.
#
# Released under a modified BSD license, please see license.txt for full terms.
# DM-0002138
#
# KD-Cloudlet includes and/or makes use of the following Third-Party Software subject to their own licenses:
# MiniMongo
# Copyright (c) 2010-2014, Steve Lacy
# All rights reserved. Released under BSD license.
# https://github.com/MiniMongo/minimongo/blob/master/LICENSE
#
# Bootstrap
# Copyright (c) 2011-2015 Twitter, Inc.
# Released under the MIT License
# https://github.com/twbs/bootstrap/blob/master/LICENSE
#
# jQuery JavaScript Library v1.11.0
# http://jquery.com/
# Includes Sizzle.js
# http://sizzlejs.com/
# Copyright 2005, 2014 jQuery Foundation, Inc. and other contributors
# Released under the MIT license
# http://jquery.org/license
__author__ = 'Sebastian'

######################################################################################################################
# Interface for a device that can be used for a Secure Key Authorization exchange.
######################################################################################################################

class ISKADevice:

    # To be called on each execution of the server before starting to use a device type.
    @staticmethod
    def initialize(root_folder):
        raise NotImplementedError()

    # To be called when bootstrapping or re-bootstrapping the server.
    @staticmethod
    def bootstrap():
        raise NotImplementedError()

    @staticmethod
    def list_devices():
        raise NotImplementedError()

    def get_name(self):
        raise NotImplementedError()

    def get_port(self):
        raise NotImplementedError()

    def get_friendly_name(self):
        raise NotImplementedError()

    def connect(self):
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()

    # DATA needs to be a dictionary of key-value pairs (the value is not used, only the key, but the value has to be non-empty).
    def get_data(self, data):
        raise NotImplementedError()

    # DATA needs to be a dictionary of key-value pairs.
    def send_data(self, data):
        raise NotImplementedError()

    def send_file(self, file_path, file_id):
        raise NotImplementedError()
