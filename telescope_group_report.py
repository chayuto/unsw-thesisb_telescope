
from ryu.base import app_manager
from ryu.controller import dpset
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_3 as ofctl
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.ofproto import ofproto_v1_3 as ofp
from ryu.ofproto import ofproto_v1_3_parser as parser
from time import time
from ryu.lib import hub

from netaddr import IPNetwork, IPAddress

import threading
#import thread
from copy import deepcopy
import time, os, random, json, datetime

from influxdb import InfluxDBClient

from ryu.app.wsgi import ControllerBase, WSGIApplication
import json
import logging
import ast
from webob import Response

'''
Telescope multi,group,exact match table 

del config pipeline tableid all 
set config pipeline tableid 0 tablesize 65536 tablewidth 32 tabletype exactmatch 
set config pipeline tableid 1 tablesize 2048 tablewidth 20 tabletype wildcardmatch 
set config pipeline apply
set config table tableid 0 matchfields 0 5 10 11 12 13 14 15 16
set config table tableid 1 matchfields 0 5 10 11 12 

sudo ryu-manager telescope_dual_link.py --verbose
'''

#TELESCOPE CONFIG
LOG = logging.getLogger('ryu.app.telescope_multi')
NOVI_48_DPID = 0x0000000000000064
NOVI_16_DPID = 0x0000000000000045
STAT_DPID = NOVI_16_DPID
TELE_VER = "V3.1"
TELE_APP_NAME = "telescope dual link"
TELE_RELEASE_DATE = "03-10-2016"


BRO_UNSW_INSTANCE_ID = 1
BRO_DORM_INSTANCE_ID = 2

TABLE_REACT = 0 
TABLE_PROACT = 1

#configurable DB
INFLUXDB_DB = "flowBucket"
INFLUXDB_HOST = "129.94.5.44"
INFLUXDB_PORT = 8086
INFLUXDB_USER = ""
INFLUXDB_PASS = ""

MONITORING_YOUTUBE = True
MONITORING_FACEBOOK = True
MONITORING_NETFLIX = True
MONITORING_IVIEW = True

PORT_GATEWAY = 4 #pica 8
PORT_SPIRENT = 8 #spirent
PORT_CLIENT = 6 #uniwideSDN
PORT_MIRROR = 2
PORT_DORM = 16
PORT_MIRROR_DORM = 14

GROUP_DEFAULT = 1
GROUP_DEFAULT_DORM = 2
GROUP_MIRROR_ID = 100
GROUP_MIRROR_DORM_ID = 200
GROUP_REACT = 1000
GROUP_REACT_DORM = 2000

applications = ["youtube","facebook","netflix","iview"]
applications_indexes = [0,1,2,3]
provider = ["uniwide","dorm"]
provider_indexes = [0,1]
n_provider = len(provider)
n_application = len(applications)

#for each provider
default_group_base_ids = [GROUP_DEFAULT,GROUP_DEFAULT_DORM]
mirror_group_base_ids = [GROUP_MIRROR_ID,GROUP_MIRROR_DORM_ID]
react_group_base_ids = [GROUP_REACT,GROUP_REACT_DORM]

group_ids = []

for index_provider in provider_indexes:
    #default 
    group_id = default_group_base_ids[index_provider] 
    group_ids.append(group_id)

    for index_app in applications_indexes:
        #mirror
        group_id = mirror_group_base_ids[index_provider] + index_app
        group_ids.append(group_id)
       
        #react
        group_id = react_group_base_ids[index_provider] + index_app
        group_ids.append(group_id)

def ship_points_to_influxdb(points):
    client = InfluxDBClient(
        host=INFLUXDB_HOST, port=INFLUXDB_PORT,
        username=INFLUXDB_USER, password=INFLUXDB_PASS,
        database=INFLUXDB_DB, timeout=10)
    return client.write_points(points=points, time_precision='ms')


class TelescopeApiController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(TelescopeApiController, self).__init__(req, link, data, **config)
        self.dpset = data['dpset']
        self.waiters = data['waiters']
        self.react_cookie_offset = 0 
        self.controllerStat = data['controllerStat']
        self.aggreatedUsage = data['aggUsageStat']  
        self.calDict = data['ipStat'] 
        self.usageDict = data['flowStat'] 
        self.groupStat = data['groupStat']

        #IP lists
        self.nfNetworkList = []
        self.googleNetworkList = []
        self.AARNetworkList = []
        self.iViewNetworkList = []
        self.facebookNetworkList = []
        self.spirentVideoList = []
        
        #load ip list from file
        servListRAW = tuple(open('./Netflix_AS2906', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.nfNetworkList.append(IPNetwork(i.strip()))
        self.nfNetworkList.append(IPNetwork("103.2.116.58/32"))

        servListRAW = tuple(open('./Google_AS15169', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.googleNetworkList.append(IPNetwork(i.strip()))

        servListRAW = tuple(open('./Facebook', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.facebookNetworkList.append(IPNetwork(i.strip()))

        servListRAW = tuple(open('./IView', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.iViewNetworkList.append(IPNetwork(i.strip()))

        self.AARNetworkList.append(IPNetwork("203.5.76.205/24"))


    def isNetflixIP(self,ip_src):

        for network in self.nfNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isGoogleIP(self,ip_src):
        for network in self.googleNetworkList:
            if IPAddress(ip_src) in network:
                return True

        for network in self.AARNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isIviewIP(self,ip_src):
        for network in self.iViewNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isFacebookIP(self,ip_src):
        for network in self.facebookNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isSpirentVideoIP(self,ip_src):
        for network in self.spirentVideoList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def clientIpToGroupOffset(self,ip_src):

        if(self.isNetflixIP(ip_src)):
            return 2
        elif(self.isGoogleIP(ip_src)):
            return 0
        elif(self.isFacebookIP(ip_src)):
            return 1
        elif(self.isIviewIP (ip_src)):
            return 3
        else :
            return 0
        
    def get_dpids(self, req, **_kwargs):
        LOG.debug('get_dpids')
        dps = list(self.dpset.dps.keys())
        body = json.dumps(dps)
        return Response(content_type='application/json', body=body)

    def get_stats(self, req, **_kwargs):
        
        LOG.debug('get_stats')
        
        outDict = {}
        mList = [];
        flowList = [];

        #reformat data for reporting
        for ip_src in self.calDict:

            srcDict = self.calDict[ip_src]
            for ip_dst in srcDict:
                entryDict = srcDict[ip_dst]

                #only report if it has significant traffics
                #if (entryDict["isVideo"]):

                newDict = {}
                newDict["time"] = entryDict["time"]
                newDict["srcIp"] = ip_src
                newDict["dstIp"] = ip_dst
                newDict["beginTime"] = entryDict["beginTime"]
                newDict["duration"] =entryDict["duration"]
                newDict["byte"] = entryDict["byte"]
                newDict["tag"] = entryDict["tag"]
                newDict["isVideo"] = entryDict["isVideo"]
                newDict["provider"] = entryDict["provider"]


                if "endpoint" in entryDict:
                  newDict["endpoint"] =  entryDict["endpoint"] 

                if "Mbps" in entryDict:
                  newDict["mbps"] = entryDict["Mbps"]
                if "quality" in entryDict:
                  newDict["quality"]= entryDict["quality"]
                mList.append(newDict)

        #sorting 
        mList = sorted(mList, key=lambda k: k["beginTime"],reverse=True) 


        for cookie in self.usageDict:
            flowEntry = self.usageDict[cookie]
            flowList.append(flowEntry)

        #sorting 
        flowList = sorted(flowList, key=lambda k: k["time"],reverse=True) ;
        
        outDict["flows"] = mList;
        outDict["usage"] = self.aggreatedUsage
        outDict["stats"] = flowList;
        
        outDict["controllerStat"] = self.controllerStat
        outDict["groupStat"] = self.groupStat

        body = json.dumps(outDict)

        res = Response(content_type='application/json', body=body)
        res._headerlist.append(('Access-Control-Allow-Origin', '*'))
        
        return res

    def classC_reactive_flow_mod(self,dp,in_port,group_id, srcIP,dstIP,src_port,dst_port):

        match = parser.OFPMatch(ipv4_src=srcIP,ipv4_dst=dstIP,
            in_port=in_port,eth_type = 0x0800,ip_proto = 6,tcp_src = src_port, tcp_dst = dst_port)
        priority = 20000 
        idle_timeout = 20

        #action1 = parser.OFPActionOutput(PORT_CLIENT);
        action1 = parser.OFPActionGroup(group_id);
        actions = [action1] #
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,actions)]
        
        mod = parser.OFPFlowMod(datapath=dp, cookie= (0x47470000 + int((time.time())*100000)),
                                priority=priority, table_id = TABLE_REACT, 
                                match=match, command=ofp.OFPFC_ADD,instructions=inst, hard_timeout=0,
                                idle_timeout=idle_timeout,out_group = group_id)

        self.react_cookie_offset += 1
        
        return mod


    def add_reactive_flow(self, req, cmd, **_kwargs):
        LOG.debug('add_reactive_flow')

        clientNetwork = IPNetwork("129.94.5.64/27")
        dorm_clientNetwork = IPNetwork("149.171.0.0/16") 

        try:
            data = ast.literal_eval(req.body)

            dpid = data.get('dpid')
            ip_dst = data.get('ip_dst')
            port_dst = data.get('port_dst')
            ip_src = data.get('ip_src')
            port_src = data.get('port_src')
            instance_id = data.get('instance_id')

        except SyntaxError:
            LOG.debug('invalid syntax %s', req.body)
            return Response(status=400)

        if type(dpid) == str and not dpid.isdigit():
            LOG.debug('invalid dpid %s', dpid)
            return Response(status=400)

        dp = self.dpset.get(int(dpid))

        if dp is None:
            return Response(status=404)

        LOG.debug(ip_dst)
        LOG.debug(port_dst)
        LOG.debug(ip_src)
        LOG.debug(port_src)


        if instance_id == BRO_UNSW_INSTANCE_ID:
            if IPAddress(ip_dst) in clientNetwork:
                #this is expected, downstream packet to client
                LOG.debug('uniwide reactive flow')
                dp.send_msg(self.classC_reactive_flow_mod(dp,PORT_GATEWAY,GROUP_REACT + self.clientIpToGroupOffset(ip_src),ip_src,ip_dst,port_src,port_dst))
               
            elif IPAddress(ip_src) in clientNetwork:
                #somehow bro screwup the source and destination
                #reverse them 
                LOG.debug('uniwide reactive flow - reversed')
                dp.send_msg(self.classC_reactive_flow_mod(dp,PORT_GATEWAY,GROUP_REACT + self.clientIpToGroupOffset(ip_src) ,ip_dst,ip_src,port_dst,port_src))
    
        elif instance_id == BRO_DORM_INSTANCE_ID:

            if IPAddress(ip_dst) in dorm_clientNetwork:
                LOG.debug('dorm reactive flow')
                dp.send_msg(self.classC_reactive_flow_mod(dp,PORT_DORM,GROUP_REACT_DORM + self.clientIpToGroupOffset(ip_src) ,ip_src,ip_dst,port_src,port_dst))
             
            elif IPAddress(ip_src) in dorm_clientNetwork:
                LOG.debug('dorm reactive flow - reversed')
                dp.send_msg(self.classC_reactive_flow_mod(dp,PORT_DORM,GROUP_REACT_DORM + self.clientIpToGroupOffset(ip_src),ip_dst,ip_src,port_dst,port_src))
        else:
            LOG.debug('WTF#$%^&*(*&^%$')

        

        return Response(status=200)

'''RYU main component'''

class telescope_multi(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(telescope_multi
       ,self).__init__(*args, **kwargs)

        self.datapaths = {}
        self.logger.debug("Init");

        self.resolution = 1
        
        #our internal record fpr stat
        self.usageDict = {} #raw info with port level stat
        self.proactiveDict = {}
        self.calDict = {} #byte count, IP level
        
        
        self.groupStatPointsToDB = []
        self.l3StatPointsToDB = []

        #initialize group stat report
        self.groupStat = {}
        for group_id in group_ids:
            self.groupStat[group_id]={}
            self.groupStat[group_id]["byte_count"] = 0
            self.groupStat[group_id]["ref_count"] = 0
            self.groupStat[group_id]["packet_count"] = 0
            self.groupStat[group_id]["rate"] = 0
            self.groupStat[group_id]["time"] = 0

        self.controllerStat = {}
        self.controllerStat["startTime"] = int(time.time());
        self.controllerStat["appName"] = TELE_APP_NAME
        self.controllerStat["version"] = TELE_VER
        self.controllerStat["releaseDate"] = TELE_RELEASE_DATE
        self.controllerStat["cummulativeReactFlowCount"] = 0
        self.controllerStat["cummulativeDBEntryCount"] = 0

        #initiate empty dict
        self.aggreatedUsage = {}
        self.aggreatedUsage["totalBytes"] = 0;
        self.aggreatedUsage["netflixBytes"] = 0;
        self.aggreatedUsage["otherBytes"] = 0;
        self.aggreatedUsage["googleBytes"] = 0
        self.aggreatedUsage["facebookBytes"] = 0
        self.aggreatedUsage["iviewBytes"] = 0
        self.aggreatedUsage["spirentVideoBytes"] = 0
        self.aggreatedUsage["mirroredBytes"] = 0
        self.aggreatedUsage["defaultBytes"] = 0;
        self.aggreatedUsage["netflixRate"] = 0;
        self.aggreatedUsage["otherRate"] = 0;
        self.aggreatedUsage["googleRate"] = 0
        self.aggreatedUsage["facebookRate"] = 0
        self.aggreatedUsage["iviewRate"] = 0
        self.aggreatedUsage["spirentVideoRate"] = 0
        self.aggreatedUsage["mirroredRate"] = 0
        self.aggreatedUsage["defaultRate"] = 0;
        self.aggreatedUsage["time"] = 0;

        self.oldAggUsage =  deepcopy(self.aggreatedUsage)

        self.recvwindow = 0

        #IP lists
        self.nfNetworkList = []
        self.googleNetworkList = []
        self.AARNetworkList = []
        self.iViewNetworkList = []
        self.facebookNetworkList = []
        self.spirentVideoList = []
        
        #load ip list from file
        servListRAW = tuple(open('./Netflix_AS2906', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.nfNetworkList.append(IPNetwork(i.strip()))
        self.nfNetworkList.append(IPNetwork("103.2.116.58/31")) # ix.asn.au

        servListRAW = tuple(open('./Google_AS15169', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.googleNetworkList.append(IPNetwork(i.strip()))

        servListRAW = tuple(open('./Facebook', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.facebookNetworkList.append(IPNetwork(i.strip()))

        servListRAW = tuple(open('./IView', 'r'))
        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
            self.iViewNetworkList.append(IPNetwork(i.strip()))

        self.AARNetworkList.append(IPNetwork("203.5.76.205/24"))

        
#        servListRAW = tuple(open('./SpirentNonVideo', 'r'))
#        for i in servListRAW:
            #servList.append(i.strip()) #remove \n character at the end of the line
#            self.spirentNonVideoList.append(IPNetwork(i.strip()))

        self.logger.debug("starting monitoring tread");
        self.monitor_thread = hub.spawn(self._monitor)

        self.logger.debug("starting webob server");
        self.dpset = kwargs['dpset']
        wsgi = kwargs['wsgi']
        self.waiters = {}
        self.data = {}
        self.data['dpset'] = self.dpset
        self.data['waiters'] = self.waiters
        self.data['controllerStat'] = self.controllerStat
        self.data['aggUsageStat'] = self.aggreatedUsage
        self.data['ipStat'] = self.calDict
        self.data['flowStat'] = self.usageDict
        self.data['groupStat'] = self.groupStat

        mapper = wsgi.mapper

        wsgi.registory['TelescopeApiController'] = self.data
        path = '/stats'
        uri = path + '/switches'
        mapper.connect('stats', uri,
                       controller=TelescopeApiController, action='get_dpids',
                       conditions=dict(method=['GET']))

        path = '/stats'
        uri = path + '/controller'
        mapper.connect('stats', uri,
                       controller=TelescopeApiController, action='get_stats',
                       conditions=dict(method=['GET']))

        path = '/reacts'
        uri = path + '/add/{cmd}'
        mapper.connect('stats', uri,
                       controller=TelescopeApiController, action='add_reactive_flow',
                       conditions=dict(method=['POST']))

    def _monitor(self):
        tmp = 0
        while True:
            #self.bc.processInput();
            self.logger.debug("Monitor");

            #sent stats point to DB and reset
            if self.groupStatPointsToDB:
                ship_points_to_influxdb(deepcopy(self.groupStatPointsToDB))
                self.groupStatPointsToDB = []

            if self.l3StatPointsToDB:
                ship_points_to_influxdb(deepcopy(self.l3StatPointsToDB))
                self.l3StatPointsToDB = []

            self.update_stats_report()

            for dp in self.datapaths.values():

                if dp.id == STAT_DPID:
                    self._request_stats(dp)
                    
                    self.recvwindow = 0
            hub.sleep(self.resolution)


    def _request_stats(self,datapath):
        #self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        #req = parser.OFPFlowStatsRequest(datapath,table_id=1)
        datapath.send_msg(req)

        #all group to report
        req = parser.OFPGroupStatsRequest(datapath, 0)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])

    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                #self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                #self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        #self.logger.info("switch_features_handler")

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        

        self.default_groups_initiation(datapath)
        time.sleep(0.2)
        self.default_flows_initiation(datapath)

        
        self.proactive_flows_install(datapath,in_port = PORT_GATEWAY,base_group_id = GROUP_MIRROR_ID)

        self.proactive_flows_install(datapath,in_port = PORT_DORM,base_group_id = GROUP_MIRROR_DORM_ID)


    def default_groups_initiation(self,datapath):

        self.logger.info("default_groups_initiation")

        weight = 100
        watch_port = 0
        watch_group = 0 

        #default flow for uniwide
        action1 = [parser.OFPActionOutput(PORT_CLIENT,0)]
        buckets = [parser.OFPBucket(weight,watch_port,watch_group,action1)]
        mod = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,  ofp.OFPGT_ALL, GROUP_DEFAULT, buckets)
        datapath.send_msg(mod)

        #default flow for dorm
        action1 = []
        buckets = [parser.OFPBucket(weight,watch_port,watch_group,action1)]
        mod = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,  ofp.OFPGT_ALL, GROUP_DEFAULT_DORM, buckets)
        datapath.send_msg(mod)

        #for class B flow mod uniwide_sdn

        for index in applications_indexes: 
            actionForward = parser.OFPActionOutput(PORT_CLIENT,0);
            actionMirror = parser.OFPActionOutput(PORT_MIRROR,0);
            action_1 = [actionMirror];
            action_2 = [actionForward];
            buckets_2 = [parser.OFPBucket(weight,watch_port,watch_group,action_1), 
                parser.OFPBucket(weight,watch_port,watch_group,action_2)]
            mod = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,  ofp.OFPGT_ALL, GROUP_MIRROR_ID + index, buckets_2)
            datapath.send_msg(mod)


        #class B flow form
        for index in applications_indexes:
            actionMirror = parser.OFPActionOutput(PORT_MIRROR_DORM,0);
            action_2 = [actionMirror];
            buckets_2 = [parser.OFPBucket(weight,watch_port,watch_group,action_2)]
            mod = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,  ofp.OFPGT_ALL, GROUP_MIRROR_DORM_ID + index, buckets_2)
            datapath.send_msg(mod)

 
        #class C flow mod for uni_wide
        for index in applications_indexes:
            actionForward = parser.OFPActionOutput(PORT_CLIENT,0);
            action_set = [actionForward];
            buckets = [parser.OFPBucket(weight,watch_port,watch_group,action_set)]
            mod = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,  ofp.OFPGT_ALL, GROUP_REACT+index, buckets)
            datapath.send_msg(mod)

        #class C flow mod for dorm
        for index in applications_indexes:
            action_set = [];
            buckets = [parser.OFPBucket(weight,watch_port,watch_group,action_set)]
            mod = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,  ofp.OFPGT_ALL, GROUP_REACT_DORM+index, buckets)
            datapath.send_msg(mod)

    def default_flows_initiation(self,datapath):

        self.logger.info("default_flows_initiation")

        self.NFdatapath = datapath

        #default table 0 miss
        priority = 0
        match = parser.OFPMatch()
        inst= [parser.OFPInstructionGotoTable(TABLE_PROACT)]
        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x39,  priority=priority, table_id = TABLE_REACT, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)
        datapath.send_msg(mod);

        #default table 1 miss
        priority = 0
        match = parser.OFPMatch()
        inst = []
        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x39,  priority=priority, table_id = TABLE_PROACT, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)
        datapath.send_msg(mod);


        #======== proactive table ==========
        priority = 100
        s_priority = 150
        ip = "129.94.5.96"
        mask = "255.255.255.224"
        ip2 = "129.94.5.128"
        mask2 = "255.255.255.128"

        #-----  server -> client ----- 

        match = parser.OFPMatch(in_port=PORT_GATEWAY)
        action1 = parser.OFPActionGroup(GROUP_DEFAULT);
        #action1 = parser.OFPActionOutput(PORT_CLIENT,0);
        actions = [action1]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        
        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x44,  priority=priority, table_id = TABLE_PROACT, out_group = GROUP_DEFAULT, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)
        '''
        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x44,  priority=priority, table_id = TABLE_PROACT, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)
        '''
        datapath.send_msg(mod);

        #----- Client -> Server -----  
        match = parser.OFPMatch(in_port=PORT_CLIENT)
        action1 = parser.OFPActionOutput(PORT_GATEWAY,0);
        actions = [action1]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x45,  priority=priority, table_id = TABLE_PROACT,
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)
        datapath.send_msg(mod);


         #----- Dorm -> Drop -----  
        match = parser.OFPMatch(in_port=PORT_DORM)
        action1 = parser.OFPActionGroup(GROUP_DEFAULT_DORM);
        actions = [action1]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x44,  priority=priority,
                                table_id = TABLE_PROACT, out_group = GROUP_DEFAULT_DORM, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)
        datapath.send_msg(mod);

        #----- dns capture ------

        '''
        priority_dns = 200;
        match = parser.OFPMatch(in_port=PORT_GATEWAY,eth_type = 0x0800,ip_proto = 17,udp_src = 53)
        #action1 = parser.OFPActionGroup(GROUP_DEFAULT);

        actionForward = parser.OFPActionOutput(PORT_CLIENT,0);
        actionMirror = parser.OFPActionOutput(PORT_MIRROR,0);
        actions = [actionForward,actionMirror];

        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = parser.OFPFlowMod(datapath=datapath, cookie=0x51,  priority=priority_dns, table_id = TABLE_PROACT, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,
                                idle_timeout=0)

        datapath.send_msg(mod);

        '''

    def proactive_flows_install(self,datapath,in_port,base_group_id):

        self.logger.info("proactive_flows_install")

        cookie_offset = 0

        if MONITORING_NETFLIX:

            netflix_src_list = tuple(open('./Netflix_AS2906', 'r'))
            for netflix_srcc in netflix_src_list:
                netflix_src=netflix_srcc.strip()

                flowmods = self.classB_flows_mod(datapath, in_port,base_group_id+2,netflix_src,cookie_offset)
                cookie_offset +=1
                # self.logger.info("after creating flowmods")
                datapath.send_msg(flowmods)

            flowmods = self.classB_flows_mod(datapath, in_port,base_group_id+2,"103.2.116.58/31",cookie_offset)
            cookie_offset +=1
            datapath.send_msg(flowmods)

        if MONITORING_FACEBOOK:

            src_list = tuple(open('./Facebook', 'r'))
            for srcc in src_list:
                src=srcc.strip()
                flowmods = self.classB_flows_mod(datapath, in_port,base_group_id+1,src,cookie_offset)
                cookie_offset +=1
                datapath.send_msg(flowmods)

        if MONITORING_IVIEW:

            src_list = tuple(open('./IView', 'r'))
            for srcc in src_list:
                src=srcc.strip()
                flowmods = self.classB_flows_mod(datapath, in_port,base_group_id+3,src,cookie_offset)
                cookie_offset +=1
                datapath.send_msg(flowmods)


        if (MONITORING_YOUTUBE):

            google_src_list = tuple(open('./Google_AS15169', 'r'))
            for google_srcc in google_src_list:
                google_src=google_srcc.strip()

                flowmods = self.classB_flows_mod(datapath, in_port,base_group_id+0,google_src,cookie_offset)
                cookie_offset +=1
                datapath.send_msg(flowmods)
            
            #AARNET
            flowmods = self.classB_flows_mod(datapath, in_port,base_group_id+0,"203.5.76.205/24",cookie_offset)
            cookie_offset +=1
            datapath.send_msg(flowmods)

        '''
        

        src_list = tuple(open('./SpirentVideo', 'r'))
        for srcc in src_list:
            src=srcc.strip()
            flowmods = self.spirent_flows_mod(datapath,src,cookie_offset)
            cookie_offset +=1
            datapath.send_msg(flowmods)

        '''

    def classB_flows_mod(self,dp, in_port, group_id, ip_block_src,cookie_offset):

        self.logger.info("classB_flows_mod: " +  ip_block_src)
        datapath = dp

        parser = datapath.ofproto_parser

        src_ip = ip_block_src
        part=src_ip.split("/")
        ip=part[0]
        mask_no = int(part[1])

        #genious solution
        mask = '.'.join([str((0xffffffff << (32 - mask_no) >> i) & 0xff) for i in [24, 16, 8, 0]])

        match = parser.OFPMatch(in_port=in_port,eth_type = 0x0800,ip_proto = 6,ipv4_src=(ip,mask)) #eth_type = 0x0800,
        # self.logger.info("after ofpmatch")
        priority = 10000
        
        action1 = parser.OFPActionGroup(group_id);
        actions = [action1] #

        #actions = [action1 ] #
        self.logger.info("after actions")
        # self.logger.info("dp: %s, srcIp: %s match: %s priority: %s actions: %s", datapath, src_ip, match, priority, actions)
        
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                             actions)]
        # self.logger.info("after inst")


        mod = parser.OFPFlowMod(datapath=datapath, cookie=(0x3309 + cookie_offset),
                                priority=priority, table_id = TABLE_PROACT, 
                                match=match, command=ofp.OFPFC_ADD, instructions=inst, hard_timeout=0,out_group = group_id,
                                idle_timeout=0)
        return mod
    
    ''' checking '''
    def isNetflixIP(self,ip_src):

        for network in self.nfNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isGoogleIP(self,ip_src):
        for network in self.googleNetworkList:
            if IPAddress(ip_src) in network:
                return True

        for network in self.AARNetworkList:
            if IPAddress(ip_src) in network:
                return True

        return False

    def isIviewIP(self,ip_src):
        for network in self.iViewNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isFacebookIP(self,ip_src):
        for network in self.facebookNetworkList:
            if IPAddress(ip_src) in network:
                return True
        return False

    def isSpirentVideoIP(self,ip_src):
        for network in self.spirentVideoList:
            if IPAddress(ip_src) in network:
                return True
        return False


    @set_ev_cls(ofp_event.EventOFPGroupStatsReply, MAIN_DISPATCHER)
    def _group_stats_reply_handler(self, ev):

        if ev.msg.datapath.id != STAT_DPID:
            self.logger.info("Not monitoring DPID");
            return

        for stat in ev.msg.body:

            group_report = ('group_id=%d '
                          'ref_count=%d packet_count=%d byte_count=%d '
                          'duration_sec=%d duration_nsec=%d' %
                          (stat.group_id,
                           stat.ref_count, stat.packet_count,
                           stat.byte_count, stat.duration_sec,
                           stat.duration_nsec))

            if stat.group_id not in group_ids:
                continue
            
            rate = 0.0
            if self.groupStat[stat.group_id]["byte_count"] == 0:
                rate = 0.0
            else:
                rate = (stat.byte_count-self.groupStat[stat.group_id]["byte_count"])*8/1e6/self.resolution
            
            self.groupStat[stat.group_id]["rate"]=rate    
            self.groupStat[stat.group_id]["ref_count"]=stat.ref_count
            self.groupStat[stat.group_id]["byte_count"]=stat.byte_count
            self.groupStat[stat.group_id]["packet_count"]=stat.packet_count
            self.groupStat[stat.group_id]["time"]=stat.duration_sec

            self.add_group_stat_point(dpid = ev.msg.datapath.id,
                group_id = stat.group_id,
                rate = rate,ref_count = stat.ref_count ,byte_count = stat.byte_count)
            
            self.logger.info('The rate is '+ str(rate))
            self.logger.info('GroupStats: %s', group_report)


    def add_group_stat_point(self,dpid,group_id,rate,ref_count,byte_count):

        tags = {
                "dpid": dpid, #int16
                "group_id":group_id
                }

        self.groupStatPointsToDB.append({
                "measurement": "groupStat",
                "tags": tags,
                "time": datetime.datetime.utcnow(),
                "fields": {
                    "rate": rate,
                    "ref_count": int(ref_count),
                    "byte_count": int(byte_count)
                 }
                  })

    ''' stat event handler'''
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):

        rcv_time = time.time()
        rcv_time2 = datetime.datetime.utcnow()
        self.recvwindow = self.recvwindow + 1
        msg = ev.msg
        body = msg.body

        if msg.datapath.id != STAT_DPID:
            self.logger.info("Not monitoring DPID");
            return

        #self.logger.info("Flow Stat received");
        fTable1 = [flow for flow in body ]; #if ((flow.cookie < 0x100) and (flow.priority<150))
        #self.logger.info("Mod1: " +str(len(fTable1)));

        for f in fTable1:
            dpid  = msg.datapath.id
            cookie = f.cookie
            packet_count = f.packet_count
            byte_count = f.byte_count

           

            if cookie == 0x44:
                self.aggreatedUsage["defaultBytes"] = byte_count


        fTable2 = [flow for flow in body if (flow.priority == 10000 and flow.table_id == TABLE_PROACT)];
        #self.logger.info("Mod2: " +str(len(fTable2)));

        for f in fTable2:
            dpid  = msg.datapath.id
            cookie = f.cookie
            packet_count = f.packet_count
            byte_count = f.byte_count

            if byte_count != 0:
                self.logger.info('table:%d cookie:%X byte_count: %d,packet_count: %d',flow.table_id,cookie,byte_count ,packet_count);

            #if byte_count > 0:
                #self.logger.info('cookie:%d byte_count: %d', cookie,byte_count);

            flowDict = {}
        
            flowDict["time"] = int(rcv_time)
            flowDict["cookie"] = cookie
            flowDict["byte"] = f.byte_count
            flowDict["duration"] = f.duration_sec
            flowDict["packets"] = f.packet_count

            self.proactiveDict[cookie] = flowDict

            sumByte = 0

            for cookie in self.proactiveDict:
                sumByte += self.proactiveDict[cookie]["byte"]

            self.aggreatedUsage["mirroredBytes"] = sumByte;



        fTable3 = [flow for flow in body if (flow.priority == 20000 
                                            and flow.table_id == TABLE_REACT)]; 
        #and flow.byte_count > 0
        #self.logger.info("Mod3: " +str(len(fTable3)));
        #and flow.byte_count > 0

        #for influx 
        points = [] 

        #[flow for flow in body if (flow.priority == 20000 and flow.table_id == 0)]
        for f in fTable3:
            #for f in [flow for flow in body]:

            dpid  = msg.datapath.id
            cookie = f.cookie
            packet_count = f.packet_count
            byte_count = f.byte_count
        
            #self.logger.info('cookie:%d byte_count: %d', cookie,byte_count);

            ip_src = str(f.match['ipv4_src'])
            ip_dst = str(f.match['ipv4_dst'])

           
            if(f.match['tcp_src'] == 80):
                endPointStr = "mobile"
            else:
                endPointStr = "web browser"

            
            flowDict = {}
            if cookie not in self.usageDict:

                flowDict["time"] = int(rcv_time)
                flowDict["cookie"] = cookie
                flowDict["sourceIP"] = ip_src
                flowDict["destinationIP"] = ip_dst 
                flowDict["tp_dst"] = f.match['tcp_dst']
                flowDict["tp_src"] = f.match['tcp_src']
                flowDict["byte"] = f.byte_count
                flowDict["duration"] = f.duration_sec
                flowDict["packets"] = f.packet_count

                #classify flow at first seen
                if(self.isNetflixIP(ip_src)):
                    flowDict["tag"] = "netflix"
                    self.aggreatedUsage["netflixBytes"] += f.byte_count;
                elif(self.isGoogleIP(ip_src)):
                    flowDict["tag"] = "google";
                    self.aggreatedUsage["googleBytes"] += f.byte_count;
                elif(self.isFacebookIP (ip_src)):
                    flowDict["tag"] = "facebook";
                    self.aggreatedUsage["facebookBytes"] += f.byte_count;
                elif(self.isIviewIP (ip_src)):
                    flowDict["tag"] = "iView";
                    self.aggreatedUsage["iviewBytes"] += f.byte_count;
                else:
                    flowDict["tag"] = "other";


                clientNetwork = IPNetwork("129.94.5.64/27")
                dorm_clientNetwork = IPNetwork("149.171.0.0/16") 

                if IPAddress(ip_dst) in clientNetwork:
                    flowDict["provider"] = "uniwide";
                elif IPAddress(ip_dst) in dorm_clientNetwork:
                    flowDict["provider"] = "dorm";
                else:
                    flowDict["provider"] = "other";

                self.usageDict[cookie] = flowDict

                #add count for flow that not found in dictionary
                self.controllerStat["cummulativeReactFlowCount"] += 1

                tags = {
                "dpid": dpid, #int16
                "dst_ip": ip_dst,
                "src_ip": ip_src,
                "src_port":f.match['tcp_src'],
                "dst_port":f.match['tcp_dst'],
                "flow_id":cookie,
                "attribute_provider":flowDict["provider"],
                "attribute_user":endPointStr,
                "attribute_others":flowDict["tag"]
                }

                #append point to influx Entry
                points.append({
                    "measurement": "flowStat",
                    "tags": tags,
                    "time": rcv_time2,
                    "fields": {
                        "byte_count": int(f.byte_count),
                        "packet_count": int(f.packet_count),
                        "duration": int(f.duration_sec),
                        "duration_nsec" : f.duration_nsec
                     }
                      })


            else:
                flowDict = self.usageDict[cookie]

                byteIncrement = f.byte_count - flowDict["byte"]
                timeIncrement = int(rcv_time) - flowDict["time"]

                if(byteIncrement < 0):
                    self.logger.info("!!! HEY its negative!");
                    self.logger.info("Counts: %d %d",f.byte_count , flowDict["byte"]);
                    self.logger.info("Time: %d %d", int(rcv_time) , flowDict["time"]);
                    self.logger.info("cookie: %d %d", cookie, f.cookie);
                    self.logger.info("port: %s %s", flowDict["tp_dst"], f.match['tcp_dst']);
                    raise ValueError('!!! HEY its negative!')

                    continue;

                #add increment to total NF counter
                if(flowDict["tag"] == "netflix"):
                    self.aggreatedUsage["netflixBytes"] += byteIncrement;
                elif(flowDict["tag"] == "google"):
                    self.aggreatedUsage["googleBytes"] += byteIncrement;
                elif(flowDict["tag"] == "facebook"):
                    self.aggreatedUsage["facebookBytes"] += byteIncrement;
                elif(flowDict["tag"] == "iView"):
                    self.aggreatedUsage["iviewBytes"] += byteIncrement;
                elif(flowDict["tag"] == "spirentVideo"):
                    self.aggreatedUsage["spirentVideoBytes"] += byteIncrement;
                else:
                    self.aggreatedUsage["otherBytes"] += byteIncrement;

                flowDict["time"] = int(rcv_time)
                flowDict["byte"] = f.byte_count
                flowDict["duration"] = f.duration_sec
                flowDict["packets"] = f.packet_count

                self.usageDict[cookie] = flowDict

                tags = {
                "dpid": dpid, #int16
                "dst_ip": ip_dst,
                "src_ip": ip_src,
                "src_port":f.match['tcp_src'],
                "dst_port":f.match['tcp_dst'],
                "flow_id":cookie,
                "attribute_provider":flowDict["provider"],
                "attribute_user":endPointStr,
                "attribute_others":flowDict["tag"]
                }

                #append point to influx Entry
                points.append({
                    "measurement": "flowStat",
                    "tags": tags,
                    "time": rcv_time2,
                    "fields": {
                        "byte_count": int(f.byte_count),
                        "packet_count": int(f.packet_count),
                        "duration": int(f.duration_sec),
                        "duration_nsec" : f.duration_nsec
                     }
                      })

                #calDict is IP level stat keeping
                '''MBPS calculation'''
                if ip_src not in self.calDict:

                    #first seen, but 0 byte
                    if byteIncrement == 0:
                        continue

                    #first entry
                    entryDict = {}
                    entryDict["id"] = cookie #cookie of the first seen flow 
                    entryDict["byte"] = byteIncrement;
                    entryDict["time"] = int(rcv_time);
                    entryDict["beginTime"] = int(rcv_time); # time first receive IP pairs
                    entryDict["duration"] = 0
                    entryDict["TimePrevious"] = int(rcv_time);
                    entryDict["BytePrevious"] = byteIncrement;
                    entryDict["TimePrevious2"] = int(rcv_time);
                    entryDict["BytePrevious2"] = byteIncrement;
                    entryDict["endpoint"] = endPointStr
                    entryDict["tag"] = flowDict["tag"]
                    entryDict["provider"] = flowDict["provider"]
                    entryDict["isVideo"] = False;

                    dstDict = {}
                    dstDict[ip_dst] = entryDict
                    self.calDict[ip_src] = dstDict

                    self.add_l3_stat_point(stat_id = entryDict["id"],
                        dpid=NOVI_16_DPID,
                        application=entryDict["tag"],
                        provider = entryDict["provider"],
                        src_ip =ip_src,
                        dst_ip = ip_dst,
                        byte_count=entryDict["byte"],
                        duration = entryDict["duration"])

                else:
                    dstDict = self.calDict[ip_src]

                    if ip_dst not in dstDict:
                        
                        #first seen, but 0 byte
                        if byteIncrement == 0:
                            continue

                        #first entry
                        entryDict = {}
                        entryDict["id"] = cookie #cookie of the first seen flow
                        entryDict["byte"] = byteIncrement;
                        entryDict["time"] = int(rcv_time);
                        entryDict["beginTime"] = int(rcv_time); # time first receive IP pairs
                        entryDict["duration"] = 0
                        entryDict["TimePrevious"] = int(rcv_time);
                        entryDict["BytePrevious"] = byteIncrement;
                        entryDict["TimePrevious2"] = int(rcv_time);
                        entryDict["BytePrevious2"] = byteIncrement;
                        entryDict["endpoint"] = endPointStr
                        entryDict["tag"] = flowDict["tag"]
                        entryDict["provider"] = flowDict["provider"]
                        entryDict["isVideo"] = False;
                        dstDict[ip_dst] = entryDict

                        self.add_l3_stat_point(stat_id = entryDict["id"],
                            dpid=NOVI_16_DPID,
                            application=entryDict["tag"],
                            provider = entryDict["provider"],
                            src_ip = ip_src,
                            dst_ip = ip_dst,
                            byte_count=entryDict["byte"],
                            duration = entryDict["duration"])

                    else:

                        entryDict = dstDict[ip_dst]
                        newByteCount = entryDict["byte"] + byteIncrement;

                        entryDict["byte"] = newByteCount 
                        entryDict["time"] = int(rcv_time);
                        entryDict["duration"] = int(rcv_time) - entryDict["beginTime"];

                        if entryDict["duration"] > 5:
                            flowMbps = float(entryDict["byte"]) * 8 / (entryDict["duration"]  * 1024 * 1024);
                            if (flowMbps > 0.5):
                                entryDict["isVideo"] = True;
                            elif (flowMbps < 0.3):
                                entryDict["isVideo"] = False;

                        timeDiff = int(rcv_time) - entryDict["TimePrevious2"]
                        totalByteInc = newByteCount  - entryDict["BytePrevious2"]

                        if timeDiff > 30:

                            #reset previous record
                            entryDict["TimePrevious2"] = int(rcv_time);
                            entryDict["BytePrevious2"] = newByteCount;

                            if entryDict["duration"] > 60:

                                #entryDict["Mbps"] = Mbps

                                Mbps = float(totalByteInc) * 8 / (timeDiff  * 1024 * 1024)
                                
                                if "Mbps" in entryDict:
                                    entryDict["Mbps"] = Mbps * (0.7) + entryDict["Mbps"] * (0.3)
                                else:
                                    entryDict["Mbps"] = Mbps
                                
                                if Mbps > 30:
                                    QualityStr = "???"
                                elif Mbps > 15:
                                    QualityStr = "UHD"
                                    entryDict["quality"] = QualityStr
                                elif Mbps > 4:
                                    QualityStr = "HD"
                                    entryDict["quality"] = QualityStr
                                elif Mbps > 1:
                                    QualityStr = "SD"
                                    entryDict["quality"] = QualityStr
                                elif Mbps > 0.5:
                                    QualityStr = "LOW"
                                    entryDict["quality"] = QualityStr
                                else:
                                    pass

                        self.add_l3_stat_point(stat_id = entryDict["id"],
                            dpid=NOVI_16_DPID,
                            application=entryDict["tag"],
                            provider = entryDict["provider"],
                            src_ip = ip_src,
                            dst_ip = ip_dst,
                            byte_count=entryDict["byte"],
                            duration = entryDict["duration"])


        #delete old inactive flow
        flowToDelete = []
        for cookie in self.usageDict:
            #if no update from switch more than 5 sec. 
            if int(rcv_time) - self.usageDict[cookie]["time"] > 5:
                flowToDelete.append(cookie)

        for cookie in flowToDelete:
            del self.usageDict[cookie]

        #delete old ip-flows 
        flowToDelete = {}
        for ip_dst,dstDict in self.calDict.items():
            for ip_src,entryDict in dstDict.items():
                if int(rcv_time) - entryDict["time"] > 15:
                    del self.calDict[ip_dst][ip_src]


        if points:
            #send datapoint to influx
            self.controllerStat["cummulativeDBEntryCount"] += len(points)
            ship_points_to_influxdb(deepcopy(points))
            pass

    def add_l3_stat_point(self,stat_id,dpid,application,provider,src_ip,dst_ip,byte_count,duration):

        tags = {
                "application": application,
                "provider":provider,
                "src_ip":src_ip,
                "dst_ip":dst_ip,
                "stat_id":stat_id
                }

        self.l3StatPointsToDB.append({
                "measurement": "l3Stat",
                "tags": tags,
                "time": datetime.datetime.utcnow(),
                "fields": {
                    "duration": int(duration),
                    "byte_count": int(byte_count)
                 }
                  })

    def calculateMbps(self,timeDiff,byteNew,byteOld):

        return  float(byteNew-byteOld) * 8 / (timeDiff  * 1024 * 1024);

    def update_stats_report(self):

        timestamp = time.time()

        self.aggreatedUsage["time"] = timestamp

        timeDiff = timestamp - self.oldAggUsage["time"] 

        self.controllerStat["uptime"] = int(timestamp)- self.controllerStat["startTime"] 

        self.aggreatedUsage["totalBytes"] = self.aggreatedUsage["defaultBytes"] + \
            self.aggreatedUsage["netflixBytes"] + \
            self.aggreatedUsage["facebookBytes"] + \
            self.aggreatedUsage["iviewBytes"] + \
            self.aggreatedUsage["spirentVideoBytes"] + \
            self.aggreatedUsage["otherBytes"] + \
            self.aggreatedUsage["mirroredBytes"] + \
            self.aggreatedUsage["googleBytes"]

        self.aggreatedUsage["defaultRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["defaultBytes"],self.oldAggUsage["defaultBytes"]) 
        self.aggreatedUsage["totalRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["totalBytes"],self.oldAggUsage["totalBytes"])
        self.aggreatedUsage["netflixRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["netflixBytes"],self.oldAggUsage["netflixBytes"])
        self.aggreatedUsage["facebookRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["facebookBytes"],self.oldAggUsage["facebookBytes"])
        self.aggreatedUsage["iviewRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["iviewBytes"],self.oldAggUsage["iviewBytes"])
        self.aggreatedUsage["otherRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["otherBytes"],self.oldAggUsage["otherBytes"])
        self.aggreatedUsage["mirroredRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["mirroredBytes"],self.oldAggUsage["mirroredBytes"])
        self.aggreatedUsage["googleRate"] = self.calculateMbps(timeDiff,self.aggreatedUsage["googleBytes"],self.oldAggUsage["googleBytes"])

        self.oldAggUsage =  deepcopy(self.aggreatedUsage)


