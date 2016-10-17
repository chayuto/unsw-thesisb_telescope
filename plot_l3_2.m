close all 
clear all

[time,flow_id,duration,byte_count,src_ip,dst_ip] = load_l3_fn('/Users/chayut/Dropbox/2016 Documents/UNSW 4.2/ELEC4120 Thesis/Thesis B/161018/l3Stat_dorm_google.csv');


uniqueIds = unique(flow_id(~any(isnan(flow_id),2),:));

length = size(time,1);
n_ids = size(uniqueIds,1);

min_time = min(time);

results = zeros(n_ids,6);

for i = 1:n_ids
    
    indexes = find(flow_id==uniqueIds(i));
     
    abs_time = time(indexes);
    y = byte_count(indexes);
    durations = duration(indexes);
    
    x = (abs_time - min_time)./1000;
    %x = (abs_time - min(abs_time))./1000;
    max_byte = max(y);
    flow_duration =  max(durations)-20;
    
    if flow_duration > 30
        mbps = max_byte*8.0  / ((flow_duration) * (1024^2) );
    else 
        mbps = NaN;
    end
    
    results(i,:) = [min(abs_time),max(abs_time),uniqueIds(i),max_byte,flow_duration,mbps];
    if mbps > 0.5
        figure(1)
        plot(x,y)
        hold on
    end
    title('Video traffic flow byte count verus Time (over period of 24 hours)');
    xlabel('time (s)');
    ylabel('flow byte count (byte)');
end
hold off

%%

results = results((results(:,5)>0),:);
results = results((results(:,6)>0.5),:);
results_google = results;
figure(2)
histogram(results(:,5),30)
xlabel('flow length (s)');
ylabel('number of flows');

totalFlowCount = size(results,1)
meanLength =  mean(results(:,5))
maxLength =  max(results(:,5))
meanMbps = mean(results(~isnan(results(:,6)),6))
maxMbps = max(results(~isnan(results(:,6)),6))
nServer = size(unique(src_ip),1)
nClient = size(unique(dst_ip),1)

%%
x=[];
y=[];
res = 30; %min
for i = 1:1:23*(60/res)
    
    time_from = min_time + res*60*1000*(i-1);
    time_to = min_time + res*60*1000*(i);
    
    flows = results(((results(:,1))>time_from) & ((results(:,1))<time_to),:);
 
    y = [y, size(flows,1)];
    timestamp =  datetime( (time_from/1000), 'ConvertFrom', 'posixtime' ); 
    x = [x, timestamp];
end

figure(3)
bar(datenum(x),y)
datetick('x','HHPM')
xlabel('time');
ylabel('active flows');

%%
%7
[time,flow_id,duration,byte_count,src_ip,dst_ip] = load_l3_fn('/Users/chayut/Dropbox/2016 Documents/UNSW 4.2/ELEC4120 Thesis/Thesis B/161018/l3Stat_dorm_facebook.csv');

uniqueIds = unique(flow_id(~any(isnan(flow_id),2),:));

length = size(time,1);
n_ids = size(uniqueIds,1);

min_time = min(time);

results = zeros(n_ids,6);

for i = 1:n_ids
    
    indexes = find(flow_id==uniqueIds(i));
     
    abs_time = time(indexes);
    y = byte_count(indexes);
    durations = duration(indexes);

    x = (abs_time - min_time)./1000;
    %x = (abs_time - min(abs_time))./1000;
    max_byte = max(y);
    flow_duration =  max(durations)-20;
    
    if flow_duration > 30
        mbps = max_byte*8.0  / ((flow_duration) * (1024^2) );
    else 
        mbps = NaN;
    end
    
    results(i,:) = [min(abs_time),max(abs_time),uniqueIds(i),max_byte,flow_duration,mbps,];
    if mbps > 0.5
        figure(4)
        plot(x,y)
        hold on
    end
    title('Video traffic flow byte count verus Time (over period of 24 hours)');
    xlabel('time (s)');
    ylabel('flow byte count (byte)');
end
hold off

%%

results = results((results(:,5)>0),:);
results = results((results(:,6)>0.5),:);
results_facebook = results;

figure(5)
histogram(results(:,5),30)
xlabel('flow length (s)');
ylabel('number of flows');

totalFlowCount = size(results,1)
meanLength =  mean(results(:,5))
maxLength =  max(results(:,5))
meanMbps = mean(results(~isnan(results(:,6)),6))
maxMbps = max(results(~isnan(results(:,6)),6))
nServer = size(unique(src_ip),1)
nClient = size(unique(dst_ip),1)



%%
x=[];
y=[];
res = 30; %min
for i = 1:1:23*(60/res)
    
    time_from = min_time + res*60*1000*(i-1);
    time_to = min_time + res*60*1000*(i);
    
    flows = results(((results(:,1))>time_from) & ((results(:,1))<time_to),:);
 
    y = [y, size(flows,1)];
    timestamp =  datetime( (time_from/1000), 'ConvertFrom', 'posixtime' ); 
    x = [x, timestamp];
end

figure(6)
datenum(x)
datetick('x','HHPM')
xlabel('time');
ylabel('active flows');


%%
%
[time,flow_id,duration,byte_count,src_ip,dst_ip] = load_l3_fn('/Users/chayut/Dropbox/2016 Documents/UNSW 4.2/ELEC4120 Thesis/Thesis B/161018/l3Stat_dorm_netflix.csv');

uniqueIds = unique(flow_id(~any(isnan(flow_id),2),:));

length = size(time,1);
n_ids = size(uniqueIds,1);

min_time = min(time);

results = zeros(n_ids,6);

for i = 1:n_ids
    
    indexes = find(flow_id==uniqueIds(i));
     
    abs_time = time(indexes);
    y = byte_count(indexes);
    durations = duration(indexes);

    x = (abs_time - min_time)./1000;
    %x = (abs_time - min(abs_time))./1000;
    max_byte = max(y);
    flow_duration =  max(durations)-20;
    
    if flow_duration > 30
        mbps = max_byte*8.0  / ((flow_duration) * (1024^2) );
    else 
        mbps = NaN;
    end
    
    results(i,:) = [min(abs_time),max(abs_time),uniqueIds(i),max_byte,flow_duration,mbps,];
    if mbps > 0.5
        figure(4)
        plot(x,y)
        hold on
    end
    title('Video traffic flow byte count verus Time (over period of 24 hours)');
    xlabel('time (s)');
    ylabel('flow byte count (byte)');
end
hold off

%%

results = results((results(:,5)>0),:);
results = results((results(:,6)>0.5),:);
results_netflix = results;

figure(5)
histogram(results(:,5),30)
xlabel('flow length (s)');
ylabel('number of flows');

totalFlowCount = size(results,1)
meanLength =  mean(results(:,5))
maxLength =  max(results(:,5))
meanMbps = mean(results(~isnan(results(:,6)),6))
maxMbps = max(results(~isnan(results(:,6)),6))
nServer = size(unique(src_ip),1)
nClient = size(unique(dst_ip),1)



%%
x=[];
y=[];
res = 30; %min
for i = 1:1:23*(60/res)
    
    time_from = min_time + res*60*1000*(i-1);
    time_to = min_time + res*60*1000*(i);
    
    flows = results(((results(:,1))>time_from) & ((results(:,1))<time_to),:);
 
    y = [y, size(flows,1)];
    timestamp =  datetime( (time_from/1000), 'ConvertFrom', 'posixtime' ); 
    x = [x, timestamp];
end

figure(6)
datenum(x)
datetick('x','HHPM')
xlabel('time');
ylabel('active flows');


%%
x=[];
y=[];
res = 30; %min
for i = 1:1:23*(60/res)
    
    time_from = min_time + res*60*1000*(i-1);
    time_to = min_time + res*60*1000*(i);
    
    flows1 = results_google(((results_google(:,1))>time_from) & ((results_google(:,1))<time_to),:);
    flows2 = results_facebook(((results_facebook(:,1))>time_from) & ((results_facebook(:,1))<time_to),:);
    flows3 = results_netflix(((results_netflix(:,1))>time_from) & ((results_netflix(:,1))<time_to),:);
    
    y = [y, [size(flows1,1);size(flows2,1);size(flows3,1)] ];
    timestamp =  datetime( (time_from/1000), 'ConvertFrom', 'posixtime' ); 
    x = [x, timestamp];
end


figure(7)
H = bar(datenum(x'),y','stacked');
datetick('x','HHPM')
xlabel('Time','FontSize',12);
ylabel('Active flows','FontSize',12);
%legend('Facebook','Youtube','Netflix');
title('Number of Active flow over Time','FontSize',12);
myC= get(gca,'ColorOrder');
for k=1:3
  set(H(k),'facecolor',myC(k+1,:))
end
AX=legend(H, {'Youtube','Facebook','Netflix'}, 'Location','Best','FontSize',12);




