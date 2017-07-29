# -*- coding: utf-8 -*-
import gluon.contrib.simplejson as json
from datetime import datetime, timedelta
from time import localtime, strftime
import calendar, random
import pytz

@auth.requires_login()
def index():
    devices = db.executesql("SELECT Device.id, Device.device_id, Device.device_name, Device.location, \
            User_Device.user_ref_id, Status.created, Status.last_ping FROM Device INNER JOIN (auth_user INNER JOIN (User_Device INNER JOIN \
            Status ON User_Device.device_ref_id = Status.device_ref_id) ON auth_user.id = User_Device.user_ref_id) \
            ON Device.id = User_Device.device_ref_id WHERE ((auth_user.username)='{}')".format(auth.user['username']))
    return dict(user_devices=devices)


@auth.requires_login()
def current_states():
    device_ref_id = request.args(0, cast=int)
    state = db.executesql("SELECT Device_States.on_or_off,Device_States.voltage,Device_States.current,Device_States.rotation,\
                            Direction.direction_type,Device_States.frequency FROM Device_States INNER JOIN Direction ON \
                            Direction.id = Device_States.direction WHERE Device_States.device_ref_id='{}'".format(device_ref_id))
    return dict(device_ref_id=device_ref_id, state=state)

@auth.requires_login()
def add_new_device():
    if request.post_vars.submit:
        device_id = request.post_vars.device_id
        device_name = request.post_vars.device_name
        device_loc = request.post_vars.location
        device_model = request.post_vars.model
        query = db.executesql("SELECT id FROM Device WHERE device_id='{}'".format(device_id))
        if not query:
            db.executesql("INSERT INTO Device (device_id,device_name,model,location) VALUES('{}','{}','{}','{}')"\
                          .format(device_id, device_name, device_model, device_loc))
            db.commit()
            device_ref_id = db.executesql("SELECT id FROM Device WHERE device_id='{}'".format(device_id))
            if device_ref_id:
                user_ref_id = db.executesql("SELECT id FROM auth_user WHERE username='{}'".format(auth.user['username']))
                db.executesql("INSERT INTO User_Device (user_ref_id,device_ref_id) VALUES('{}','{}')".format(user_ref_id[0][0],device_ref_id[0][0]))
                db.commit()
                direction = db.executesql("SELECT id FROM Direction WHERE direction_type='{}'".format('Forward'))[0][0]
                db.executesql("INSERT INTO Control_Instruction (device_ref_id,volt_flag,curr_flag,rot_flag,dir_flag,freq_flag) \
                               VALUES('{}','{}','{}','{}','{}','{}')".format(device_ref_id[0][0], '0', '0', '0', direction, '0'))
                db.commit()
                db.executesql("INSERT INTO Device_States (device_ref_id,voltage,current,rotation,direction,frequency) \
                               VALUES('{}','{}','{}','{}','{}','{}')".format(device_ref_id[0][0],'0','0','0',direction,'0'))
                db.commit()
                dt = datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%Y-%m-%d %H:%M:%S")
                time = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                db.executesql("INSERT INTO Status (device_ref_id,created,last_ping,server_time) VALUES('{}','{}','{}','{}')"\
                              .format(device_ref_id[0][0], time, time, time))
                db.commit()
                db.executesql("INSERT INTO Changes (device_ref_id, change_flag) VALUES('{}','{}')".format(device_ref_id[0][0],'1'))
                db.commit()
                response.flash='Successfully registered'
        else:
            response.flash='Device is already registered!'
    return dict()


auth.requires_login()
def device_controller():
    if request.args(0, cast=int):
        device_ref_id = request.args(0, cast=int)
        id = db.executesql("SELECT id FROM Control_Instruction WHERE device_ref_id ='{}'".format(device_ref_id))
        if id:
            db.Control_Instruction.id.readable = db.Control_Instruction.id.writable = False
            db.Control_Instruction.device_ref_id.readable = db.Control_Instruction.device_ref_id.writable = False
            db.Control_Instruction.off_flag.readable = db.Control_Instruction.off_flag.writable = False
            db.Control_Instruction.freq_flag.readable = db.Control_Instruction.freq_flag.writable = False
            form = SQLFORM(db.Control_Instruction, id[0][0], showid=False).process(next=URL('default','change_status',args=device_ref_id))
            #form.elements('input',_id='onoff')[0]['_type'] = 'button'
            return dict(form = form)
        else:
            return None

def change_status():
    if request.args(0, cast=int):
        device_ref_id = request.args(0, cast=int)
        db.executesql("UPDATE Changes SET change_flag='{}' WHERE device_ref_id='{}'".format('1', device_ref_id))
        db.commit()
        redirect(URL('default','index'))

def changes():
    if request.vars.deviceid:
        dt = datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%Y-%m-%d %H:%M:%S")
        ping = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        server_time = datetime.now()
        device_id = request.vars.deviceid
        query = db.executesql("SELECT id FROM Device WHERE device_id='{}'".format(device_id))
        if query:
            db.Status.update_or_insert(db.Status.device_ref_id==query[0][0],device_ref_id=query[0][0],last_ping=ping,server_time=ping)
            db.commit()
            change = db.executesql("SELECT change_flag FROM Changes INNER JOIN Device \
                                    ON Device.id = Changes.device_ref_id WHERE Device.device_id='{}'".format(device_id))[0][0]
            return dict(change=change)
    else:
        return None

def get_instruction():
    if request.vars.deviceid:
        dt = datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%Y-%m-%d %H:%M:%S")
        ping = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        server_time = datetime.now()
        device_id = request.vars.deviceid
        query = db.executesql("SELECT id FROM Device WHERE device_id='{}'".format(device_id))
        if query:
            db.Status.update_or_insert(db.Status.device_ref_id==query[0][0],device_ref_id=query[0][0],last_ping=ping,server_time=ping)
            db.commit()
            state = db.executesql("SELECT Control_Instruction.volt_flag, Control_Instruction.curr_flag, \
                Control_Instruction.freq_flag, Control_Instruction.onoff_flag, Control_Instruction.rot_flag, \
                Direction.direction_type FROM Device INNER JOIN (Control_Instruction INNER JOIN Direction \
                ON Direction.id = Control_Instruction.dir_flag) ON (Device.id = Control_Instruction.device_ref_id) \
                WHERE Device.device_id='{}'".format(device_id))

            # for loop should be removed
            jsonlst = []
            record = {"voltage":state[0][0],"current":state[0][1],"frquency":state[0][2],"onoff":state[0][3],\
                      "rotation":state[0][4],"direction":state[0][5]}
            jsonlst.append(record)
            return dict(device_info = jsonlst)
        else:
            return None
    else:
        return None

def data_received():
    if request.vars.deviceid:
        dt = datetime.now(pytz.timezone('Asia/Dhaka')).strftime("%Y-%m-%d %H:%M:%S")
        ping = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        server_time = datetime.now()
        device_id = request.vars.deviceid
        query = db.executesql("SELECT id FROM Device WHERE device_id='{}'".format(device_id))
        if query:
            db.Status.update_or_insert(db.Status.device_ref_id==query[0][0], device_ref_id=query[0][0], last_ping=ping, server_time=ping)
            db.commit()
            state = db.executesql("SELECT Control_Instruction.onoff_flag,Control_Instruction.volt_flag,Control_Instruction.curr_flag,\
                                   Control_Instruction.rot_flag,Direction.id,Control_Instruction.freq_flag FROM Device \
                                   INNER JOIN (Control_Instruction INNER JOIN Direction ON Direction.id = Control_Instruction.dir_flag) \
                                   ON (Device.id = Control_Instruction.device_ref_id) WHERE Device.device_id='{}'".format(device_id))

            db.executesql("UPDATE Device_States SET on_or_off='{}',voltage='{}',current='{}',rotation='{}',direction='{}',frequency='{}' \
                           WHERE device_ref_id='{}'".format(state[0][0],state[0][1],state[0][2],state[0][3],state[0][4],state[0][5],query[0][0]))
            db.commit()
            db.executesql("UPDATE Changes SET change_flag='{}' WHERE device_ref_id='{}'".format('0', query[0][0]))
            db.commit()
            return 'success'
        else:
            return 'failed'
    else:
        return 'request with your device id'


@auth.requires_login()
def delete_device():
    user_devices = db.executesql("SELECT Device.id,Device.device_name,Device.location FROM Device INNER JOIN \
                   (auth_user INNER JOIN User_Device ON auth_user.id = User_Device.user_ref_id) \
                   ON Device.id = User_Device.device_ref_id WHERE ((auth_user.username)='{}')".format(auth.user['username']))
    form = SQLFORM.factory(
        Field('action'),
        Field('device_ref_id', readable=False)
    )
    if form.process().accepted:
        action = form.vars.action.lower()
        device_ref_id = form.vars.device_ref_id
        if action == "yes" or action == "y":
            redirect(URL('delete_device', args=device_ref_id))
    if request.args(0):
        device_ref_id = request.args(0, cast=int)
        db.executesql("DELETE FROM Device WHERE id='{}'".format(device_ref_id))
        session.flash ='Deleted successfully'
        redirect(URL('default','delete_device'))
    return dict(user_devices=user_devices,form=form)

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())


@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()
