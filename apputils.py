#
########################################################################################################################
#
#
#  	Project     	: 	Water Tank Level Reader
#
#   File            :   apputils.py
#
#	By              :   George Leonard ( georgelza@gmail.com )
#
#   Created     	:   14 May 2022
#
#   Notes       	:
#
#######################################################################################################################

__author__      = "George Leonard"
__email__       = "georgelza@gmail.com"
__version__     = "0.0.1"
__copyright__   = "Copyright 2020, George Leonard"

import configparser

def get_config_params(configfile, descriptor=""):
    """ Get/Read config file contents """

    parser = configparser.ConfigParser()
    parser.read(configfile)

    params = {}
    for section_name in parser.sections():
        items = {}
        for itemname, itemvalue in parser.items(section_name):
            items[itemname] = itemvalue
        params[section_name] = items

    return params
# end def 

