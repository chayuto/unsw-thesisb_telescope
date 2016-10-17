
import requests
import time as Time
from broccoli import *

from netaddr import IPNetwork, IPAddress


netflix_src_list = tuple(open('./Netflix_AS2906', 'r'))
networkList =[]
for i in netflix_src_list:
	#servList.append(i.strip()) #remove \n character at the end of the line
	networkList.append(IPNetwork(i.strip()))

def post_to_controller(dpid,instance_id,ip_src,port_src,ip_dst,port_dst):

	url = 'http://129.94.5.44:8080/reacts/add/me'
	data = {"dpid":dpid,"instance_id":instance_id,"ip_src":ip_src,"port_src":port_src,"ip_dst":ip_dst,"port_dst":port_dst}
	print data


	try:

		r = requests.post(url, json=data)


		result = r.status_code

		if result == 200:
			print 'POST success'
		else:
			print result
			pass
	except:
		print data
		print 'error'


@event
def new_con_detect(c,d,a,b):
	#hack swap source and destination

	global recv
	recv += 1
	print "==== Con %d ====" % recv
	print repr(a), a
	print repr(b), b
	print repr(c), c
	print repr(d), d

	parts1 = b.split("/")
	port_src = int(parts1[0])
	parts2 = d.split("/")
	port_dst = int(parts2[0])

	dpid = 69
	instance_id = 1
	#dpid = 100
	ip_src = str(a)
	ip_dst = str(c)
	post_to_controller(dpid,instance_id,ip_src,port_src,ip_dst,port_dst);

	#not necesssary but just to be sure
	for network in networkList:
		if IPAddress(a) in network:
			break;

@event 

def test_event():
	print "==== test_event ===="


@event(addr, port, addr, port, count, int)
def new_syn_detect(a,b,c,d,win_size,win_scale):
	#hack swap source and destination

	global recv
	recv += 1
	print "==== SYN %d ====" % recv
	print repr(a), a
	print repr(b), b
	print repr(c), c
	print repr(d), d
	print repr(win_size), win_size
	print repr(win_scale), win_scale

@event(addr, port, addr, port, string, addr)
def dns_detect(a,b,c,d,query,answer):
	#hack swap source and destination

	global recv
	recv += 1
	print "==== DNS %d ====" % recv
	print repr(a), a
	print repr(b), b
	print repr(c), c
	print repr(d), d
	print repr(query), query
	print repr(answer), answer

	'''
	dpid = 100
	ip_src = str(a)
	ip_dst = str(c)
	post_to_controller(dpid,ip_src,port_src,ip_dst,port_dst);

	#not necesssary but just to be sure
	for network in networkList:
		if IPAddress(a) in network:
			break;
	'''


recv = 0 
bc = Connection("129.94.5.86:47758")

while True:
	bc.processInput();

	Time.sleep(0.1)


