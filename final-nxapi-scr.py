import xmltodict
import json
import re
from device import Device
import types
import sys

debug = False


def checkroutes(sw):

    #load command variable with xml from this command
    command = sw.show('show ip route')

    result = xmltodict.parse(command[1])

    #define variables
    i = 0
    routeloop = False

    #run through each route looking for route uptime
    while i < len(result['ins_api']['outputs']['output']['body']['TABLE_vrf']['ROW_vrf']['TABLE_addrf']['ROW_addrf']['TABLE_prefix']['ROW_prefix']):
        t1 = 0
        t2 = 0
        #assign uptime value to variable
        uptime = result['ins_api']['outputs']['output']['body']['TABLE_vrf']['ROW_vrf']['TABLE_addrf']['ROW_addrf']['TABLE_prefix']['ROW_prefix'][i]['TABLE_path']['ROW_path'][0]['uptime']
        i += 1
        # print uptime
        #using regex assign number of days route has been up to a variable
        day = re.findall(r'\P(.*)D', uptime)
        # print "Day:"  + str(day)
        for days in day:
            t1=days
            # print t1
        #using regesx assign number of hours route has been up to a variable
        hour = re.findall(r'\T(.*)H', uptime)
        for hours in hour:
            t2=hours
            # print t2
        if hour == []:
            t2 = 0
        # print "Hour " + str(hour)
        if int(t1) < 1 and int(t2) < 1:
        	routeloop = True

    #check if routes have been up less than an hour or not
    if routeloop:
        print "You have routes that are less than 1 hour old. Possible routes flapping(loop)"
    else:
    	print "Routes look good."

    return routeloop

def stp_detail(switch):
	"""stp_detail uses 'show spanning-tree detail' command to determine if there is been a STP topology change on the switch.
	"""

	ifloop = False
	stp_split = []

	getdata = switch.conf('show spanning-tree detail | inc Number')

	if debug:
		print getdata

	show_stp = xmltodict.parse(getdata[1])

	stp = show_stp ['ins_api']['outputs']['output']['body']

	tcn_change = re.findall('(?<=occurred\s).*(?=\:)', stp)
	for each in tcn_change:
		for time in tcn_change:

			first_hour = re.findall(r'^(.*):',time)
			for hour in first_hour:
				if int(hour) == 0:
					ifloop = True
			#pulls the hour as an integer from the time listed in the message body

			first_minute = re.findall(r'\:(.*)',time)
			for minute in first_minute:
				if int(minute) <= 5:
					ifloop = True
			#pulls the minute as an integer from the time listed in the message body

			stp_time = hour + ':' + minute
			if debug:
				print stp_time

		if debug:
			print "Last topology change happened " + stp_time + " hours ago"

	tcn_number = re.findall('(?<=changes\s).*(?=\last)', stp)
	for number in tcn_number:
		stp_number = number
	#pulls ths number of topology changes that have occurred if tcn_change returns a value in the specified range

		if debug:
			print "Number of topology changes = " + stp_number

	if ifloop:
		print "Last topology change happened " + stp_time + " hours ago"
		print "Number of topology changes = " + stp_number
	else:
		print "No STP topology changes."

def get_ip_protocols(sw):
	protocols = []
	ospf = test_ospf(sw)
	if ospf:
		protocols.append("ospf")
	eigrp = test_eigrp(sw)
	if eigrp:
		protocols.append("eigrp")
	bgp = test_bgp(sw)
	if bgp:
		protocols.append("bgp")
	return protocols

def test_ospf(sw):
	"""Test_ospf uses various show commands to determine if OSPF is running on the switch.
	"""
	cmd = cmd = sw.show('show ip ospf')
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']

	try:
		if resp["code"] == "400":
			#most likely feature ospf is not in the configuration.
			return False
		elif resp["code"] == "501" and resp["clierror"] == "Note:  process currently not running\n":
			#feature ospf is enabled but not configured.
			return False
		elif resp["code"] == "200":
			#ospf appears to be configured
			contexts = resp["body"]["TABLE_ctx"]["ROW_ctx"]
			if len(contexts) > 0:
				return True
	except Exception as oops:
		print type(oops)
		print oops.args
		print oops
	return False

def test_eigrp(sw):
	"""Test_eigrp uses various show commands to determine if EIGRP is running on the switch.
	"""
	cmd = sw.show('show ip eigrp')
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']

	try:
		if resp["code"] == "400":
			#most likely feature eigrp is not in the configuration.
			return False
		elif resp["code"] == "501" and resp["clierror"] == "Note:  process currently not running\n":
			#feature eigrp is enabled but not configured.
			return False
		elif resp["code"] == "200":
			#eigrp appears to be configured
			contexts = resp["body"]["TABLE_asn"]["ROW_asn"]
			if len(contexts) > 0:
				return True
	except Exception as oops:
		print type(oops)
		print oops.args
		print oops
	return False

def get_ospf_interfaces(sw):
	"""Get_ospf_interfaces returns a list of interfaces where OSPF has a neighbor relationship"""
	cmd = sw.show('show ip ospf neighbors')
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']

	if resp["code"] != "200" or resp["body"] == "":
		return []
	nbrcount = int(resp["body"]["TABLE_ctx"]["ROW_ctx"]["nbrcount"])
	interfaces = set()
	nbrrow = resp["body"]["TABLE_ctx"]["ROW_ctx"]["TABLE_nbr"]["ROW_nbr"]
	if nbrcount > 1:
		for nbr in nbrrow:
			if nbr["intf"] not in interfaces:
				interfaces.add(nbr["intf"])
	elif nbrcount == 1:
		if nbrrow["intf"] not in interfaces:
				interfaces.add(nbrrow["intf"])
	return list(interfaces)

def get_bgp_interfaces(sw):
	"""Get_bgp_interfaces returns a list of interfaces used to reach a BGP peer."""
	cmd = sw.conf("show ip bgp neighbors")
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']

	if resp["code"] != "200":
		return []
	#look for "BGP neighbor is #.#.#.#"
	#print resp["body"]
	interfaces = set()
	for peer in re.findall("BGP neighbor is ([0-9.]*),", resp["body"]):
		if peer != None:
			# print "Peer IP: " + peer
			intf_list = get_ip_route_interfaces(sw, peer)
			# print "DEBUG: " + str(set(intf_list))
			interfaces = interfaces.union(set(intf_list))
	return list(interfaces)

def get_eigrp_interfaces(sw):
	"""Get_eigrp_interfaces returns a list of interfaces where EIGRP has a neighbor relationship"""
	cmd = sw.show('show ip eigrp neighbors')
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']

	if resp["code"] != "200" or resp["body"] == "":
		return []
	peers = resp["body"]["TABLE_asn"]["ROW_asn"]["TABLE_vrf"]["ROW_vrf"]["TABLE_peer"]["ROW_peer"]
	interfaces = set()
	if isinstance(peers, types.ListType):
		#more than one peer
		for peer in peers:
			interfaces.add(peer["peer_ifname"])
	elif isinstance(peers, types.DictType):
		#just one peer
		interfaces.add(peers["peer_ifname"])
	else:
		#no peers?
		pass
	return list(interfaces)

def get_ip_route_interfaces(sw, ip):
	"""get_ip_route_interfaces returns the list interfaces used by the
	     local device to reach the next hop for the given ip."""
	cmd = sw.show("show ip route " + ip)
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']
	# print "DEBUG" + ip
	# print json.dumps(resp, indent=2)
	if resp["code"] != "200":
		# print "debug: show ip route bad resp - " + resp["code"]
		return []
	route_table = resp["body"]["TABLE_vrf"]["ROW_vrf"]["TABLE_addrf"]["ROW_addrf"]["TABLE_prefix"]["ROW_prefix"]
	i = 0
	interfaces = []
	while i < int(route_table["ucast-nhops"])*2:
		interfaces.append(route_table["TABLE_path"]["ROW_path"][i]["ifname"])
		i += 2
	# print "Interfaces: " + str(interfaces)
	return interfaces

def test_bgp(sw):
	"""Test_bgp uses various show commands to determine if BGP is running on the switch.
	"""
	cmd = cmd = sw.conf('show ip bgp')
	resp = xmltodict.parse(cmd[1])['ins_api']['outputs']['output']

	try:
		if resp["code"] == "400":
			#most likely feature bgp is not in the configuration.
			return False
		elif resp["code"] == "200" and resp["body"] == "Note:  process currently not running\n":
			#feature bgp is enabled but not configured.
			return False
		elif resp["code"] == "200":
			#bgp appears to be configured
			return True
	except Exception as oops:
		print type(oops)
		print oops.args
		print oops
	return False

def check_vlan_vpc(peer_list, vpc_vlan_list):
    for intf in peer_list:
        # print "DEBUG: " + str(intf)
        vlan_id = re.findall("Vlan([0-9]*)", intf)
        # print "DEBUG: " + str(vlan_id)
        if vlan_id != []:
            if int(vlan_id[0]) in vpc_vlan_list:
                print "Vlan " + vlan_id[0] + " is on the VPC peer link."

def get_vpc_vlans(sw):
    show_vpc_command = sw.show('show vpc brief')
    result_vpc_command = xmltodict.parse(show_vpc_command[1])
    peerlink_vlans=result_vpc_command['ins_api']['outputs']['output']['body']['TABLE_peerlink']['ROW_peerlink']['peer-up-vlan-bitset'].split(",")
    vlan_list = []
    for vlan in peerlink_vlans:
        vlan_list.append(int(vlan))
    return vlan_list

def main():

        switch = Device(ip='172.23.193.210', username='admin', password='P@ssw0rd')
        switch.open()

        checkroutes(switch)
        stp_detail(switch)
        protocols = get_ip_protocols(switch)
        for proto in protocols:
            print "Switch is running " + proto
        ospf_interfaces = []
        eigrp_interfaces = []
        bgp_interfaces = []
        if "ospf" in protocols:
            ospf_interfaces = get_ospf_interfaces(switch)
        if "eigrp" in protocols:
            eigrp_interfaces = get_eigrp_interfaces(switch)
        if "bgp" in protocols:
            bgp_interfaces = get_bgp_interfaces(switch)
        if len(ospf_interfaces) >= 1:
            print "OSPF has peers on interface(s): " + str(ospf_interfaces)
        if len(eigrp_interfaces) >= 1:
            print "EIGRP has peers on interface(s): " + str(eigrp_interfaces)
        if len(bgp_interfaces) >= 1:
            print "BGP has peers on interface(s): " + str(bgp_interfaces)
        vpc_vlan_list = get_vpc_vlans(switch)
        check_vlan_vpc(ospf_interfaces, vpc_vlan_list)
        check_vlan_vpc(eigrp_interfaces, vpc_vlan_list)
        check_vlan_vpc(bgp_interfaces, vpc_vlan_list)

if __name__ == "__main__":
    main()
