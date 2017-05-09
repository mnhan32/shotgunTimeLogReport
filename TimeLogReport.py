from __future__ import print_function
from shotgun_api3 import Shotgun
import os,sys,json,datetime
from  itertools import *
from operator import itemgetter
import config

def generateTimeLogReport(sg,tDayFormat):    
    #tmp var
    detailReportSwitch = 0
    missingReportSwitch = 1
    internalTimeLogProj = 108 #use 118 for test
    allGrpId = 9    
    timeLogReportGrpId = 18 
    
    logUser=[]
    cUsr=0
    timelogAmt = 0
    logPrint = 0
      
    detailReport=''
    missingInfo=''
    dep = ''
    
    home_dir = os.path.expanduser('~')
    errlog = os.path.join(home_dir+'shotgunTimeLogReport.log')  
    
    
    #get timelog data
    filterArg = [
        ['date','in_calendar_day',-1],
        ['user.HumanUser.permission_rule_set','in',[{'type':'PermissionRuleSet','id':14},{'type':'PermissionRuleSet','id':8}]]
        
    ]

    #timeLogData= sg.find('TimeLog',filters=filterArg,fields=['user','user.HumanUser.department','entity','date','project','duration'],order=[{'field_name':'user.HumanUser.department','direction':'asc'},{'field_name':'user', 'direction':'asc'},{'field_name':'date', 'direction':'asc'}])   
    timeLogData= sg.find('TimeLog',filters=filterArg,fields=['user','user.HumanUser.department','entity','date','project','duration'])   
    timeLogData = sorted(timeLogData, key=itemgetter('user.HumanUser.department','user','date'),reverse=0)
    #timeLogData = sorted(timeLogData, key=itemgetter('name','date'),reverse=1)
    #get active user in artist permission group
    filterArg = [
        ['sg_status_list','is','act'],
        ['permission_rule_set','in',[{'type':'PermissionRuleSet','id':14},{'type':'PermissionRuleSet','id':8}]]
    ]
    userData = sg.find('HumanUser',filters=filterArg,fields=['name','entity','department'])
    activeUser = [i['name'] for i in userData]

    #separate user into department group
    detailReport += '___________________________________\n\n'
    detailReport += 'Time log report on %s\n\n'%tDayFormat
    #print(timeLogData)
    
    for k1, depGrp in groupby(timeLogData, key = itemgetter('user.HumanUser.department')):
        count = 0
        dur = 0

        if not dep == k1['name']:
            dep = k1['name']
            detailReport += '*********************\n'
            detailReport += 'Department : %s\n'%dep
            detailReport += '*********************\n'
                    
        for d in depGrp:
            
            if not cUsr == d['user']['id']:
                logUser.append(d['user'])                
                cUsr = d['user']['id']
                
                if count:
                    detailReport += '       total hr in yesterday : %.2f hr.\n\n'%float(dur/60.0)
                    dur = 0                
                    
                detailReport += '   USER : %s\n'%d['user']['name']
                count = 1
                
            
            timelogAmt += 1
            eName = None
            pName = None
            if 'entity' in d.keys():
                if d['entity']:
                    eName = d['entity']['name']
            if 'project' in d.keys():
                pName = d['project']['name']
                
            dur += float(d['duration'])
            
            detailReport += '       Date : %s ,%s : %s, duration : %.2f hr.\n'%(d['date'], pName, eName, float(d['duration'])/60.0)
        
        detailReport += '       total hr in yesterday : %.2f hr.\n\n'%float(dur/60.0)    
    detailReport += '\n_____________End of Report______________\n'
    print('here')
    # 
    #generate missing timelog info if there is any

    missingUser = [i for i in userData if i['id'] not in [j['id'] for j in logUser] and sg.work_schedule_read(tDayFormat,tDayFormat,None, i)[tDayFormat]['working'] == True]
    if missingUser:
        missingReport=[]        
        missingInfo = 'Missing time log (%s) from the following users :'%tDayFormat
        missingDep = ''
        for i,j in groupby(missingUser, lambda o: o['department']):
            if not missingDep == i['name']:
                missingDep = i['name']
                missingInfo += '\n__________\nDept. %s\n__________\n'%missingDep
                
            for p in j:
                #Each missing user 
                missingReport.append({'type':'HumanUser','id':p['id']})              
                missingInfo += '    %s\n'%p['name']
                
        if missingReportSwitch:
                             
            noteData = {
                'project':{'type':'Project','id':internalTimeLogProj},
                'code':'Missing TimeLog %s'%tDayFormat,
                'sg_contents': missingInfo,    
                'addressings_to':missingReport,
                'addressings_cc':[{'type':'Group','id':timeLogReportGrpId}]
            }
      
            sg.create('CustomThreadedEntity01',noteData)
        else:
            print(missingInfo)
            pass                
    else:
        if sg.work_schedule_read(tDayFormat,tDayFormat,None, None)[tDayFormat]['working'] == True:
            if missingReportSwitch:
                noteData = {                
                    'project':{'type':'Project','id':internalTimeLogProj},
                    'code':'No Missing TimeLog %s'%tDayFormat,
                    'sg_contents': 'There is no missing time log.',    
                    'addressings_cc':[{'type':'Group','id':timeLogReportGrpId}]
                }
            
            sg.create('CustomThreadedEntity01',noteData)

            else:
                #print('No missing timelog.')
                pass
        else:
            #print('not a working day.')
            pass

    #sumbit note
    if detailReportSwitch:
        noteData = {
        'project':{'type':'Project','id':internalTimeLogProj},
        'code':'Detail Time Log Report %s'%tDayFormat,
        'sg_contents': timelogReport,
        'addressings_to':[{'type':'Group','id':timeLogReportGrpId}]
        }            
        sg.create('CustomThreadedEntity01',noteData)
    else:
        #print(detailReport)
        pass


def main():
    #server connection
    #use script_name=<script name>,api_key=<api key> to login
    sg = Shotgun(config.server,script_name=config.scriptName,api_key=config.apiKey)    
    #sg = Shotgun(config.server,login=config.userName,password=config.passWd)
   
    #get yesterday string format, check if yesterday is a work day
    tDay = datetime.datetime.today()-datetime.timedelta(1)    
    tDayFormat = tDay.strftime('%Y-%m-%d')
    tSchedule = sg.work_schedule_read(tDayFormat,tDayFormat)
    
    if tSchedule[tDayFormat]['working'] == True:
        # a work day
        try:
            generateTimeLogReport(sg,tDayFormat)
        except:
            sg.close()
            print('err')
            sys.exit()
            
    sg.close()
    sys.exit()
        
    
    
if __name__ == '__main__':
    main()


