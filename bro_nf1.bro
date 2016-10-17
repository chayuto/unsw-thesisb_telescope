

@load frameworks/communication/listen
redef Communication::listen_port = 47758/tcp;


redef Communication::nodes += {
	["broping"] = [$host = 245.0.0.1, $events = /test1/, $connect=F, $ssl=F]
};


global test2: event(a: int, b: count, c: time, d: interval, e: bool, f: double, g: string, h: port, i: addr, j: subnet, i6: addr, j6: subnet);

global new_con_detect: event(a: addr, b: port, c: addr, d: port);
global new_syn_detect: event(a: addr, b: port, c: addr, d: port, win_size: count, win_scale: int);
global dns_detect: event(a: addr, b: port, c: addr, d: port, query: string, answer: addr);
global test_event: event();

event test1(a: int, b: count, c: time, d: interval, e: bool, f: double, g: string, h: port, i: addr, j: subnet, i6: addr, j6: subnet)
{
    print "==== atomic";
    print a;
    print b;
    print c;
    print d;
    print e;
    print f;
    print g;
    print h;
    print i;
    print i6;
    print j;
    print j6;
    
    event test2(42, 42, current_time(), 1min, T, 3.14, "Hurz", 12345/udp, 1.2.3.4, 22.33.44.0/24, [2607:f8b0:4009:802::1014], [2607:f8b0:4009:802::1014]/32);
}


event dns_A_reply(c: connection, msg: dns_msg, ans: dns_answer, a: addr){
    print "----DNS A Reply----";
    print c$id$orig_h;
    print port_to_count(c$id$orig_p);
    print c$id$resp_h;
    print port_to_count(c$id$resp_p);
    print ">dns answer";
    print a;
    print ans$query;

    event dns_detect(c$id$orig_h,c$id$orig_p,c$id$resp_h, c$id$resp_p,ans$query,a);

}

event connection_SYN_packet(c: connection, pkt: SYN_packet){
    
    print "----SYN detect----";
    print c$id$orig_h;
    print port_to_count(c$id$orig_p);
    print c$id$resp_h;
    print port_to_count(c$id$resp_p);
    print get_port_transport_proto(c$id$resp_p);
    print pkt$DF;
    print pkt$win_size;
    print pkt$win_scale;

    event new_syn_detect(c$id$orig_h,c$id$orig_p,c$id$resp_h, c$id$resp_p, pkt$win_size, pkt$win_scale);
}

event new_connection(c: connection ){

    if ( get_port_transport_proto(c$id$resp_p) == tcp ){

        print "======" ;   
        print c$id$orig_h;
        print port_to_count(c$id$orig_p);
        print c$id$resp_h;
        print port_to_count(c$id$resp_p);
        print get_port_transport_proto(c$id$resp_p);

        event new_con_detect(c$id$orig_h,c$id$orig_p,c$id$resp_h, c$id$resp_p);
    }
}

