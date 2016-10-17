
ids = [2, 200,201,202,203,2000,2001,2002,2003];
%ids = [2];


min_time = min(time);
res = 30;
x = [];
y= [];
data3= []
for i = 1:1:23*(60/res)
    
    time_from = min_time + res*60*1000*(i-1);
    time_to = min_time + res*60*1000*(i);
    
    indexes_1 = (time>time_from) & (time<time_to);
    
    
    for j = 1:9
        
       sub_group_id = group_id(indexes_1);
       sub_byte_count = byte_count(indexes_1);
       index_2 = sub_group_id == ids(j) ;
       
       bytes = max(sub_byte_count(index_2)) - min(sub_byte_count(index_2));

       if isempty(bytes)
            data(1,j) = 0;
       else
           data(1,j) = bytes;
       end
       
    end
    
   %data2 = [data(:,1),data(:,2)+data(:,6),data(:,3)+data(:,7),data(:,4)+data(:,8),data(:,5)+data(:,9)];
   data2 = [data(:,1),data(:,2)+data(:,6),data(:,3)+data(:,7),data(:,4)+data(:,8)];
   data3 = [data3;data];
   
   data = data2;
    
    
    y = [y, data'/((1024^2)* res*30) ];
    timestamp =  datetime( (time_from/1000), 'ConvertFrom', 'posixtime' ); 
    x = [x, timestamp];
end

totalUsage = sum(data3,1)/(1024^3)
OtherUsage = totalUsage(1)
YouTubeUsage = totalUsage(2) + totalUsage(6)
FacebookUsage = totalUsage(3) + totalUsage(7)
NetflixUsage = totalUsage(4) + totalUsage(8)
YouTubePercentMirror = totalUsage(2)*100 / YouTubeUsage
FacebookPercentMirror = totalUsage(3)*100 / FacebookUsage
NetflixPercentMirror = totalUsage(4)*100 / NetflixUsage

PercentMirror =  (sum(totalUsage(2:4))*100/ sum(totalUsage))


H = bar(datenum(x'),y','stacked');
datetick('x','HHPM')
%legend('other','youtube','facebook','netflix','iView')
xlabel('Time','FontSize',12);
ylabel('Averaged Rate over 30 Minutes (Mbps)','FontSize',12);
title('Dorm network load','FontSize',12);

myC= get(gca,'ColorOrder');
for k=1:4
  set(H(k),'facecolor',myC(k,:))
end
AX=legend(H, {'Other','Youtube','Facebook','Netflix'}, 'Location','Best','FontSize',12);


