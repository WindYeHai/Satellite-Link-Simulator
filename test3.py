#-*- coding: UTF-8 -*-
import csv
import time
from sys import argv
import sys
import os
import paramiko
import bottle
import libvirt
import json
import gevent

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = '6666'
app=bottle.Bottle()

def run(host=None,port=None):
	host=host or DEFAULT_HOST
	port=port or DEFAULT_PORT
	return app.run(host=host,port=port)

@app.route('/v1.0/test',method='POST')
def setLink():
	instance_name=bottle.request.POST.get('instance_name')
	mac=bottle.request.POST.get('mac')
	accessfile=bottle.request.POST.get('accessfile')
	delayberfile=bottle.request.POST.get('delayberfile')	
	vport=getVport(instance_name,mac)
	print instance_name,mac,accessfile,delayberfile,vport
	linkAccess(accessfile,delayberfile,vport)

def getVport(instance_name,mac):
	conn=libvirt.open(None)
	dom=conn.lookupByName(instance_name)
	xml=dom.XMLDesc()
	macIndex=xml.find(mac)
	if macIndex==-1:
		res['result']=0
		res['info']='mac does not exist'
		resultInfo(res)
		#return 'result:0 errInfo:mac does not exist'
	vport=xml[xml.find('tap',macIndex):xml.find('tap',macIndex)+14]
	print vport
	conn.close()
	return vport

def opencsv(csvfile,rowname):
	with open(csvfile,'rb') as csvfile:
		reader = csv.DictReader(csvfile)
		rowdata = [row[rowname] for row in reader] 
		return rowdata

def interface_show(**kwargs):
	Access = ' '*5 + kwargs['access']
	lineTmpla = kwargs['title'] + "%s" 
   	lineTmpla1 = kwargs['end']
	delay = kwargs['delay']
	ber = kwargs['ber']
	vport = kwargs['vport']
    	time_remain(Access,lineTmpla,kwargs['minutes'],lineTmpla1,delay,ber,vport)
	
def time_remain(access,lineTmpla,mins,lineTmpla1,delay,ber,vport):
	if delay=="" and ber=="":
		count = 0
        	while (count < mins):
                	count += 1
                	n = mins - count
                	time.sleep(1)
                	sys.stdout.write("\r" + access + lineTmpla %(n) + lineTmpla1)
                	sys.stdout.flush()
			if not n:
                		print ""	
	else:    
		count = 0
		pacloss=bertrans(ber)
    		while (count < mins):
        
			if count % 60 == 0:
				num = count/60
				os.system('tc qdisc del dev '+vport+' root')
                		os.system('tc qdisc add dev '+vport+' root netem delay '+str(delay[num])+'ms loss '+str(pacloss[num])+'%')
				Remotessh()

			count += 1
        		n = mins - count
        		time.sleep(1)
			if n==0 and num==len(delay)-2:
                        	num += 1
        		sys.stdout.write("\r" + access + lineTmpla %(n) + lineTmpla1 +",此时链路延时为"+str(delay[num])+"ms"+",链路误码率为"+str(ber[num])+" ")
        		sys.stdout.flush()
			if not n:
                                print ""

def linkDelayAndBer(starttime,stoptime,filename):
	Time = opencsv(filename,'Time (UTCG)')
	Distance = opencsv(filename,'Range (km)')
        Distance = map(eval,Distance)
	BER = opencsv(filename,'BER')
	Time1=[]
	distance=[]
	ber=[]
	for t in range(0,len(Time)):
		Time1.append(time.mktime(time.strptime(Time[t],'%d %b %Y %H:%M:%S')))
	for i in range(0,len(Time1)):
		if Time1[i]>=starttime and Time1[i]<=stoptime:
			distance.append(Distance[i])	
			ber.append(BER[i])
	Delay = [int(s/299792458*1000000) for s in distance]
	return Delay,ber

#误码率仿真量级为10^-3~10^-6
def bertrans(bersend):
	pacloss=[]
	for i in bersend:
		bernum = float(i)*pow(10,6)
        	packetlossmin = (bernum/(1460*8)+1)/85*100
       		packetlossmax = min(bernum,85)/85*100
        	packetlossavg = (packetlossmin + packetlossmax)/2
		pacloss.append(packetlossavg)
	return pacloss


def Remotessh():
        #创建ssh对象
        ssh = paramiko.SSHClient()
        #允许连接不在know_host中的主机
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #连接服务器
        ssh.connect(hostname='192.168.1.21',port=22,username='root',password='jnopenstack')
        #执行命令
        stdin, stdout, stderr = ssh.exec_command('ip netns exec qdhcp-cac6f458-a9c5-44d9-a859-f0e3c279c313 sshpass -p ubuntu ssh 192.168.22.6 python ScapySend.py')
        #执行结果 result = stderr.read() #如果有错误则打印
#       print stderr
#        result = stdout.read()
#        res = re.findall(r"\d+\.\d% hits",result)
        #关闭连接
        ssh.close()
#        return res[0]

def linkAccess(accessfilename,testfilename,vport):
	flag = 0
#	filename = argv[1]
	StartTime = opencsv(accessfilename,'Start Time (UTCG)')
	StopTime = opencsv(accessfilename,'Stop Time (UTCG)')
	num = opencsv(accessfilename,'Access')
	for i in range(0,len(StartTime)):
		starttime = StartTime[i]
		stoptime = StopTime[i]
		starttime = time.mktime(time.strptime(starttime,'%d %b %Y %H:%M:%S'))
		stoptime = time.mktime(time.strptime(stoptime,'%d %b %Y %H:%M:%S'))
		flag = flag+1
		result = '正处于第'+str(flag)+'可见时段内'
		result1 = '正处于第'+str(flag-1)+','+str(flag)+'可见时段之间'
		t = 0
		a = 0
		b = 0
		if (flag == len(num)) and (time.time() > starttime) and (time.time() > stoptime):
			print ' '*5 + "该链路周期内已不再可通"
			os.system('tc qdisc del dev '+vport+' root')
			os.system('tc qdisc add dev '+vport+' root netem delay 30s')
			break
		if (time.time() > starttime) and (time.time() > stoptime):
			continue
		while t<2: 
			if(starttime <= time.time()) and (stoptime >= time.time()):				
				while(starttime <= time.time()) and (stoptime >= time.time()):
					delay,ber=linkDelayAndBer(time.time(),stoptime,testfilename)
					interface_show(access=result,title=",链路状态为通,",minutes=int(stoptime-time.time()),end="s后链路断开",delay=delay,ber=ber,vport=vport)				            

				a+=1

			elif(starttime > time.time()) or (stoptime < time.time()):
				os.system('tc qdisc del dev '+vport+' root')
				os.system('tc qdisc add dev '+vport+' root netem delay 30s')				
				while(starttime > time.time()) or (stoptime < time.time()):
					interface_show(access=result1,title=",链路断开,",minutes=int(starttime-time.time()),end="s后链路可通",delay="",ber="",vport=vport)		
				b+=1
				if (a==1 and b==1) or (a==1 and b==2):
					continue		
			t = t + 1
	
if __name__=='__main__':
	run('0.0.0.0','6666',server='gevent')
