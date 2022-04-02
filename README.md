# Video Traffic Telemetry using SDN
unsw-thesisb_telescope

## Problem statement
Video traffic is consuming a large portion of bandwidth in carriers’ network. Video traffic is designed to be adaptive traffic to consume bandwidth as much as possible. This is to deliver the best possible video quality from the content providers. Carriers are struggling in coping with the increasing demand and finding ways to monitor and manage such traffic


## Objective
Our objective of this project is to develop a video traffic monitoring tool using Software-Defined Networking (SDN) for ISP, that offers low-cost flow-level monitoring, providing insight of the video flow


## My solution
TeleScope: Flow-level monitoring tool for video traffic with SDN:
‘Bump-in-a-wire’ architecture with minimal disruption to data-plane forwarding
Utilise SDN commodity switch (no specialised hardware) with open-source controller
Dynamically manage rules in SDN switch to minimise processing cost
Utilise Traffic Analyser to inspect packet headers, reducing the control plane overhead


## Contributions (at most one per line, most important first)
Plan and design of the video traffic telemetry tool: TeleScope
Implement fully functional prototype in UNSW SDN Testbed
Validate solution with test scenario 
Assess scalability of the system with hardware traffic generator
Deploy system on live feed traffic and provide useful report for network operator

## Suggestions for future work
Behavioural-based classification of video using flow’s statistical data collected by TeleScope (i.e. using machine learning)
