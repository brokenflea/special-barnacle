#!/usr/bin/env python

import xmltodict
import sys
from device import Device
import types
import re
import json

def get_vpc_vlans(sw):

	show_vpc_command = sw.show('show vpc brief')
	result_vpc_command = xmltodict.parse(show_vpc_command[1])

	peerlink_vlans=result_vpc_command['ins_api']['outputs']['output']['body']['TABLE_peerlink']['ROW_peerlink']['peer-up-vlan-bitset'].split(",")

	#for each in peerlink_vlans:
	#	print 'vlan ', each['peer-up-vlan-bitset']
	return peerlink_vlans

if __name__ == "__main__":
	# switch = Device(ip='198.18.134.17', username='admin2',password='cisco')
	switch = Device(ip='172.23.193.210', username='admin',password='P@ssw0rd')

	switch.open()

	#vpc_vlans = str(get_vpc_vlans(switch))
	vpc_vlans = get_vpc_vlans(switch)

	print "The following vlan's are being carried over vPC Peer Link."
	print "Ensure these are not running any routing protos."
	print vpc_vlans
	#i = 0
	#while i < len(vpc_vlans):
	#	print(vpc_vlans[i])
	#	i += 1
	#for each in vpc_vlans:
	#	print vpc_vlans
	#for each in vpc_vlans:
	#	print 'vlan ', vpc_vlans