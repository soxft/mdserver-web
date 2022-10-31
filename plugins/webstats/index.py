# coding:utf-8

import sys
import io
import os
import time
import json

sys.path.append(os.getcwd() + "/class/core")
import mw


app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'webstats'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


sys.path.append(getPluginDir() + "/class")
from LuaMaker import LuaMaker


def listToLuaFile(path, lists):
    content = LuaMaker.makeLuaTable(lists)
    content = "return " + content
    mw.writeFile(path, content)


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getConf():
    conf = getServerDir() + "/lua/config.json"
    return conf


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def luaConf():
    return mw.getServerDir() + '/web_conf/nginx/vhost/webstats.conf'


def status():
    path = luaConf()
    if not os.path.exists(path):
        return 'stop'
    return 'start'


def loadLuaFile(name):
    lua_dir = getServerDir() + "/lua"
    lua_dst = lua_dir + "/" + name

    lua_tpl = getPluginDir() + '/lua/' + name
    content = mw.readFile(lua_tpl)
    content = content.replace('{$SERVER_APP}', getServerDir())
    content = content.replace('{$ROOT_PATH}', mw.getServerDir())
    mw.writeFile(lua_dst, content)


def loadConfigFile():
    lua_dir = getServerDir() + "/lua"
    conf_tpl = getPluginDir() + "/conf/config.json"

    content = mw.readFile(conf_tpl)
    content = json.loads(content)

    dst_conf_json = getServerDir() + "/lua/config.json"
    mw.writeFile(dst_conf_json, json.dumps(content))

    dst_conf_lua = getServerDir() + "/lua/webstats_config.lua"
    listToLuaFile(dst_conf_lua, content)


def loadLuaSiteFile():
    lua_dir = getServerDir() + "/lua"

    content = makeSiteConfig()
    for index in range(len(content)):
        pSqliteDb('web_log', content[index]['name'])

    lua_site_json = lua_dir + "/sites.json"
    mw.writeFile(lua_site_json, json.dumps(content))

    # 设置默认列表
    default_json = lua_dir + "/default.json"
    ddata = {}
    dlist = []
    for i in content:
        dlist.append(i["name"])

    dlist.append('unset')
    ddata["list"] = dlist
    if len(ddata["list"]) < 1:
        ddata["default"] = "unset"
    else:
        ddata["default"] = dlist[0]

    mw.writeFile(default_json, json.dumps(ddata))

    lua_site = lua_dir + "/webstats_sites.lua"

    tmp = {
        "name": "unset",
        "domains": [],
    }
    content.append(tmp)
    listToLuaFile(lua_site, content)


def loadDebugLogFile():
    debug_log = getServerDir() + "/debug.log"
    lua_dir = getServerDir() + "/lua"
    mw.writeFile(debug_log, '')


def pSqliteDb(dbname='web_logs', site_name='unset', name="logs"):

    db_dir = getServerDir() + '/logs/' + site_name
    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)

    file = db_dir + '/' + name + '.db'
    if not os.path.exists(file):
        conn = mw.M(dbname).dbPos(db_dir, name)
        sql = mw.readFile(getPluginDir() + '/conf/init.sql')
        sql_list = sql.split(';')
        for index in range(len(sql_list)):
            conn.execute(sql_list[index])
    else:
        conn = mw.M(dbname).dbPos(db_dir, name)

    conn.execute("PRAGMA synchronous = 0")
    conn.execute("PRAGMA page_size = 4096")
    conn.execute("PRAGMA journal_mode = wal")
    return conn


def makeSiteConfig():
    siteM = mw.M('sites')
    domainM = mw.M('domain')
    slist = siteM.field('id,name').where(
        'status=?', (1,)).order('id desc').select()

    data = []
    for s in slist:
        tmp = {}
        tmp['name'] = s['name']

        dlist = domainM.field('id,name').where(
            'pid=?', (s['id'],)).order('id desc').select()

        _t = []
        for d in dlist:
            _t.append(d['name'])

        tmp['domains'] = _t
        data.append(tmp)

    return data


def initDreplace():

    service_path = getServerDir()

    pSqliteDb()

    path = luaConf()
    path_tpl = getPluginDir() + '/conf/webstats.conf'
    if not os.path.exists(path):
        content = mw.readFile(path_tpl)
        content = content.replace('{$SERVER_APP}', service_path)
        content = content.replace('{$ROOT_PATH}', mw.getServerDir())
        mw.writeFile(path, content)

    lua_dir = getServerDir() + "/lua"
    if not os.path.exists(lua_dir):
        mw.execShell('mkdir -p ' + lua_dir)

    log_path = getServerDir() + "/logs"
    if not os.path.exists(log_path):
        mw.execShell('mkdir -p ' + log_path)

    file_list = [
        'webstats_common.lua',
        'webstats_log.lua',
    ]

    for fl in file_list:
        loadLuaFile(fl)

    loadConfigFile()
    loadLuaSiteFile()
    loadDebugLogFile()

    return 'ok'


def start():
    initDreplace()

    import tool_task
    tool_task.createBgTask()

    if not mw.isAppleSystem():
        mw.execShell("chown -R www:www " + getServerDir())

    mw.opWeb("reload")
    return 'ok'


def stop():
    path = luaConf()
    if os.path.exists(path):
        os.remove(path)

    import tool_task
    tool_task.removeBgTask()

    mw.opWeb("restart")
    return 'ok'


def restart():
    initDreplace()

    mw.opWeb("reload")
    return 'ok'


def reload():
    initDreplace()

    loadDebugLogFile()

    mw.opWeb("reload")
    return 'ok'


def getGlobalConf():
    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)
    return mw.returnJson(True, 'ok', content)


def setGlobalConf():
    args = getArgs()

    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)

    for v in ['record_post_args', 'record_get_403_args']:
        data = checkArgs(args, [v])
        if data[0]:
            rval = False
            if args[v] == "true":
                rval = True
            content['global'][v] = rval

    for v in ['ip_top_num', 'uri_top_num', 'save_day']:
        data = checkArgs(args, [v])
        if data[0]:
            content['global'][v] = int(args[v])

    for v in ['cdn_headers', 'exclude_extension', 'exclude_status', 'exclude_ip']:
        data = checkArgs(args, [v])
        if data[0]:
            content['global'][v] = args[v].split("\\n")

    data = checkArgs(args, ['exclude_url'])
    if data[0]:
        exclude_url = args['exclude_url'].strip(";")
        exclude_url_val = []
        if exclude_url != "":
            exclude_url_list = exclude_url.split(";")
            for i in exclude_url_list:
                t = i.split("|")
                val = {}
                val['mode'] = t[0]
                val['url'] = t[1]
                exclude_url_val.append(val)
        content['global']['exclude_url'] = exclude_url_val

    mw.writeFile(conf, json.dumps(content))
    conf_lua = getServerDir() + "/lua/webstats_config.lua"
    listToLuaFile(conf_lua, content)
    mw.restartWeb()
    return mw.returnJson(True, '设置成功')


def getSiteConf():
    args = getArgs()

    check = checkArgs(args, ['site'])
    if not check[0]:
        return check[1]

    domain = args['site']
    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)

    site_conf = {}
    if domain in content:
        site_conf = content[domain]
    else:
        site_conf["cdn_headers"] = content['global']['cdn_headers']
        site_conf["exclude_extension"] = content['global']['exclude_extension']
        site_conf["exclude_status"] = content['global']['exclude_status']
        site_conf["exclude_ip"] = content['global']['exclude_ip']
        site_conf["exclude_url"] = content['global']['exclude_url']
        site_conf["record_post_args"] = content['global']['record_post_args']
        site_conf["record_get_403_args"] = content[
            'global']['record_get_403_args']

    return mw.returnJson(True, 'ok', site_conf)


def setSiteConf():
    args = getArgs()
    check = checkArgs(args, ['site'])
    if not check[0]:
        return check[1]

    domain = args['site']
    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)

    site_conf = {}
    if domain in content:
        site_conf = content[domain]
    else:
        site_conf["cdn_headers"] = content['global']['cdn_headers']
        site_conf["exclude_extension"] = content['global']['exclude_extension']
        site_conf["exclude_status"] = content['global']['exclude_status']
        site_conf["exclude_ip"] = content['global']['exclude_ip']
        site_conf["exclude_url"] = content['global']['exclude_url']
        site_conf["record_post_args"] = content['global']['record_post_args']
        site_conf["record_get_403_args"] = content[
            'global']['record_get_403_args']

    for v in ['record_post_args', 'record_get_403_args']:
        data = checkArgs(args, [v])
        if data[0]:
            rval = False
            if args[v] == "true":
                rval = True
            site_conf[v] = rval

    for v in ['ip_top_num', 'uri_top_num', 'save_day']:
        data = checkArgs(args, [v])
        if data[0]:
            site_conf[v] = int(args[v])

    for v in ['cdn_headers', 'exclude_extension', 'exclude_status', 'exclude_ip']:
        data = checkArgs(args, [v])
        if data[0]:
            site_conf[v] = args[v].split("\\n")

    data = checkArgs(args, ['exclude_url'])
    if data[0]:
        exclude_url = args['exclude_url'].strip(";")
        exclude_url_val = []
        if exclude_url != "":
            exclude_url_list = exclude_url.split(";")
            for i in exclude_url_list:
                t = i.split("|")
                val = {}
                val['mode'] = t[0]
                val['url'] = t[1]
                exclude_url_val.append(val)
        site_conf['exclude_url'] = exclude_url_val

    content[domain] = site_conf

    mw.writeFile(conf, json.dumps(content))
    conf_lua = getServerDir() + "/lua/webstats_config.lua"
    listToLuaFile(conf_lua, content)
    mw.restartWeb()
    return mw.returnJson(True, '设置成功')


def getSiteListData():
    lua_dir = getServerDir() + "/lua"
    path = lua_dir + "/default.json"
    data = mw.readFile(path)
    return json.loads(data)


def getDefaultSite():
    data = getSiteListData()
    return mw.returnJson(True, 'OK', data)


def setDefaultSite(name):
    lua_dir = getServerDir() + "/lua"
    path = lua_dir + "/default.json"
    data = mw.readFile(path)
    data = json.loads(data)
    data['default'] = name
    mw.writeFile(path, json.dumps(data))
    return mw.returnJson(True, 'OK')


def toSumField(sql):
    l = sql.split(",")
    field = ""
    for x in l:
        field += "sum(" + x + ") as " + x + ","
    field = field.strip(',')
    return field


def getSiteStatInfo(domain, query_date):
    conn = pSqliteDb('request_stat', domain)
    conn = conn.where("1=1", ())

    field = 'time,req,pv,uv,ip,length'
    field_sum = toSumField(field.replace("time,", ""))

    time_field = "substr(time,1,6),"

    field_sum = time_field + field_sum
    conn = conn.field(field_sum)
    if query_date == "today":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 0 * 86400))
        conn.andWhere("time >= ?", (todayTime,))
    elif query_date == "yesterday":
        startTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 1 * 86400))
        endTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time()))
        conn.andWhere("time>=? and time<=?", (startTime, endTime))
    elif query_date == "l7":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 7 * 86400))
        conn.andWhere("time >= ?", (todayTime,))
    elif query_date == "l30":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 30 * 86400))
        conn.andWhere("time >= ?", (todayTime,))
    else:
        exlist = query_date.split("-")
        start = time.strftime(
            '%Y%m%d00', time.localtime(int(exlist[0])))
        end = time.strftime(
            '%Y%m%d23', time.localtime(int(exlist[1])))
        conn.andWhere("time >= ? and time <= ? ", (start, end,))

    # 统计总数
    stat_list = conn.inquiry(field)
    del(stat_list[0]['time'])
    return stat_list[0]


def getOverviewList():
    args = getArgs()
    check = checkArgs(args, ['site', 'query_date', 'order'])
    if not check[0]:
        return check[1]

    domain = args['site']
    query_date = args['query_date']
    order = args['order']

    setDefaultSite(domain)
    conn = pSqliteDb('request_stat', domain)
    conn = conn.where("1=1", ())

    field = 'time,req,pv,uv,ip,length'
    field_sum = toSumField(field.replace("time,", ""))

    time_field = "substr(time,1,8),"
    if order == "hour":
        time_field = "substr(time,9,10),"

    field_sum = time_field + field_sum
    conn = conn.field(field_sum)
    if query_date == "today":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 0 * 86400))
        conn.andWhere("time >= ?", (todayTime,))
    elif query_date == "yesterday":
        startTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 1 * 86400))
        endTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time()))
        conn.andWhere("time>=? and time<=?", (startTime, endTime))
    elif query_date == "l7":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 7 * 86400))
        conn.andWhere("time >= ?", (todayTime,))
    elif query_date == "l30":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 30 * 86400))
        conn.andWhere("time >= ?", (todayTime,))
    else:
        exlist = query_date.split("-")
        start = time.strftime(
            '%Y%m%d00', time.localtime(int(exlist[0])))
        end = time.strftime(
            '%Y%m%d23', time.localtime(int(exlist[1])))
        conn.andWhere("time >= ? and time <= ? ", (start, end,))

    # 统计总数
    stat_list = conn.inquiry(field)
    del(stat_list[0]['time'])

    # 分组统计
    dlist = conn.group(time_field.strip(",")).inquiry(field)

    data = {}
    data['data'] = dlist
    data['stat_list'] = stat_list[0]

    return mw.returnJson(True, 'ok', data)


def getSiteList():
    args = getArgs()
    check = checkArgs(args, ['query_date'])
    if not check[0]:
        return check[1]

    query_date = args['query_date']

    data = getSiteListData()
    data_list = data["list"]

    rdata = []
    for x in data_list:
        tmp = getSiteStatInfo(x, query_date)
        tmp["site"] = x
        rdata.append(tmp)
    return mw.returnJson(True, 'ok', rdata)


def getLogsRealtimeInfo():
    '''
    实时信息
    '''
    import datetime
    args = getArgs()
    check = checkArgs(args, ['site', 'type'])
    if not check[0]:
        return check[1]

    domain = args['site']
    dtype = args['type']

    conn = pSqliteDb('web_logs', domain)
    timeInt = time.mktime(datetime.datetime.now().timetuple())

    conn = conn.where("time>=?", (int(timeInt) - 10,))

    field = 'time,body_length'
    field_sum = toSumField(field.replace("time,", ""))
    time_field = "substr(time,1,2) as time,"
    time_field = time_field + field_sum
    clist = conn.field(time_field.strip(",")).group(
        'substr(time,1,2)').inquiry(field)

    body_count = 0
    if len(clist) > 0:
        body_count = clist[0]['body_length']

    req_count = conn.count()

    data = {}
    data['realtime_traffic'] = body_count
    data['realtime_request'] = req_count

    return mw.returnJson(True, 'ok', data)


def attacHistoryLogHack(conn, site_name, query_date='today'):
    if query_date == "today":
        return
    db_dir = getServerDir() + '/logs/' + site_name
    file = db_dir + '/history_logs.db'
    if os.path.exists(file):
        attach = "ATTACH DATABASE '" + file + "' as 'history_logs'"
        # print(attach)
        r = conn.originExecute(attach)
        sql_table = "(select * from web_logs union all select * from history_logs.web_logs)"
        # print(sql_table)
        conn.table(sql_table)


def getLogsList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'method', 'status_code', 'spider_type', 'query_date', 'search_uri'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    method = args['method']
    status_code = args['status_code']
    spider_type = args['spider_type']
    query_date = args['query_date']
    search_uri = args['search_uri']
    setDefaultSite(domain)

    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    conn = pSqliteDb('web_logs', domain)

    field = 'time,ip,domain,server_name,method,is_spider,protocol,status_code,request_headers,ip_list,client_port,body_length,user_agent,referer,request_time,uri,body_length'
    condition = ''
    conn = conn.field(field)
    conn = conn.where("1=1", ())

    if method != "all":
        conn = conn.andWhere("method=?", (method,))

    if status_code != "all":
        conn = conn.andWhere("status_code=?", (status_code,))

    if spider_type == "normal":
        pass
    elif spider_type == "only_spider":
        conn = conn.andWhere("is_spider>?", (0,))
    elif spider_type == "no_spider":
        conn = conn.andWhere("is_spider=?", (0,))
    elif int(spider_type) > 0:
        conn = conn.andWhere("is_spider=?", (spider_type,))

    todayTime = time.strftime('%Y-%m-%d 00:00:00', time.localtime())
    todayUt = int(time.mktime(time.strptime(todayTime, "%Y-%m-%d %H:%M:%S")))
    if query_date == 'today':
        conn = conn.andWhere("time>=?", (todayUt,))
    elif query_date == "yesterday":
        conn = conn.andWhere("time>=? and time<=?", (todayUt - 86400, todayUt))
    elif query_date == "l7":
        conn = conn.andWhere("time>=?", (todayUt - 7 * 86400,))
    elif query_date == "l30":
        conn = conn.andWhere("time>=?", (todayUt - 30 * 86400,))
    else:
        exlist = query_date.split("-")
        conn = conn.andWhere("time>=? and time<=?", (exlist[0], exlist[1]))

    if search_uri != "":
        conn = conn.andWhere("uri like '%" + search_uri + "%'", ())

    attacHistoryLogHack(conn, domain, query_date)

    clist = conn.limit(limit).order('time desc').inquiry()
    count_key = "count(*) as num"
    count = conn.field(count_key).limit('').order('').inquiry()
    # print(count)
    count = count[0][count_key]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.returnJson(True, 'ok', data)


def getLogsErrorList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'status_code', 'query_date'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    status_code = args['status_code']
    query_date = args['query_date']
    setDefaultSite(domain)

    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    conn = pSqliteDb('web_logs', domain)

    field = 'time,ip,domain,server_name,method,protocol,status_code,ip_list,client_port,body_length,user_agent,referer,request_time,uri,body_length'
    conn = conn.field(field)
    conn = conn.where("1=1", ())

    if status_code != "all":
        if status_code.find("x") > -1:
            status_code = status_code.replace("x", "%")
            conn = conn.andWhere("status_code like ?", (status_code,))
        else:
            conn = conn.andWhere("status_code=?", (status_code,))
    else:
        conn = conn.andWhere(
            "(status_code like '50%' or status_code like '40%')", ())

    todayTime = time.strftime('%Y-%m-%d 00:00:00', time.localtime())
    todayUt = int(time.mktime(time.strptime(todayTime, "%Y-%m-%d %H:%M:%S")))
    if query_date == 'today':
        conn = conn.andWhere("time>=?", (todayUt,))
    elif query_date == "yesterday":
        conn = conn.andWhere("time>=? and time<=?", (todayUt - 86400, todayUt))
    elif query_date == "l7":
        conn = conn.andWhere("time>=?", (todayUt - 7 * 86400,))
    elif query_date == "l30":
        conn = conn.andWhere("time>=?", (todayUt - 30 * 86400,))
    else:
        exlist = query_date.split("-")
        conn = conn.andWhere("time>=? and time<=?", (exlist[0], exlist[1]))

    attacHistoryLogHack(conn, domain, query_date)

    clist = conn.limit(limit).order('time desc').inquiry()
    count_key = "count(*) as num"
    count = conn.field(count_key).limit('').order('').inquiry()
    count = count[0][count_key]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.returnJson(True, 'ok', data)


def getClientStatList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'query_date'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    query_date = args['query_date']
    setDefaultSite(domain)

    conn = pSqliteDb('client_stat', domain)
    stat = pSqliteDb('client_stat', domain)

    # 列表
    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    field = 'time,weixin,android,iphone,mac,windows,linux,edeg,firefox,msie,metasr,qh360,theworld,tt,maxthon,opera,qq,uc,pc2345,safari,chrome,machine,mobile,other'
    field_sum = toSumField(field.replace("time,", ""))
    time_field = "substr(time,1,8),"
    field_sum = time_field + field_sum

    stat = stat.field(field_sum)
    if query_date == "today":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 0 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "yesterday":
        startTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 1 * 86400))
        endTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time()))
        stat.where("time>=? and time<=?", (startTime, endTime))
    elif query_date == "l7":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 7 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "l30":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 30 * 86400))
        stat.where("time >= ?", (todayTime,))
    else:
        exlist = query_date.split("-")
        start = time.strftime(
            '%Y%m%d00', time.localtime(int(exlist[0])))
        end = time.strftime(
            '%Y%m%d23', time.localtime(int(exlist[1])))
        stat.where("time >= ? and time <= ? ", (start, end,))

    # 图表数据
    statlist = stat.group('substr(time,1,4)').inquiry(field)

    if len(statlist) > 0:
        del(statlist[0]['time'])

        pc = 0
        pc_key_list = ['chrome', 'qh360', 'edeg', 'firefox', 'safari', 'msie',
                       'metasr', 'theworld', 'tt', 'maxthon', 'opera', 'qq', 'pc2345']

        for x in pc_key_list:
            pc += statlist[0][x]

        mobile = 0
        mobile_key_list = ['mobile', 'android', 'iphone', 'weixin']
        for x in mobile_key_list:
            mobile += statlist[0][x]
        reqest_total = pc + mobile

        sum_data = {
            "pc": pc,
            "mobile": mobile,
            "reqest_total": reqest_total,
        }

        statlist = sorted(statlist[0].items(),
                          key=lambda x: x[1], reverse=True)
        _statlist = statlist[0:10]
        __statlist = {}
        statlist = []
        for x in _statlist:
            __statlist[x[0]] = x[1]
        statlist.append(__statlist)
    else:
        sum_data = {
            "pc": 0,
            "mobile": 0,
            "reqest_total": 0,
        }
        statlist = []

    # 列表数据
    conn = conn.field(field_sum)
    clist = conn.group('substr(time,1,8)').limit(
        limit).order('time desc').inquiry(field)

    sql = "SELECT count(*) num from (\
            SELECT count(*) as num FROM client_stat GROUP BY substr(time,1,8)\
        )"
    result = conn.query(sql, ())
    result = list(result)
    count = result[0][0]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist
    data['stat_list'] = statlist
    data['sum_data'] = sum_data

    return mw.returnJson(True, 'ok', data)


def getDateRangeList(start, end):
    dlist = []
    if start > end:
        for x in list(range(start, 32, 1)):
            dlist.append(x)

        for x in list(range(1, end, 1)):
            dlist.append(x)
    else:
        for x in list(range(start, end, 1)):
            dlist.append(x)

    return dlist


def getIpStatList():
    args = getArgs()
    check = checkArgs(args, ['site', 'query_date'])
    if not check[0]:
        return check[1]

    domain = args['site']
    tojs = args['tojs']
    query_date = args['query_date']
    setDefaultSite(domain)

    conn = pSqliteDb('ip_stat', domain)

    origin_field = "ip,day,flow"

    if query_date == "today":
        ftime = time.localtime(time.time())
        day = ftime.tm_mday

        field_day = "day" + str(day)
        field_flow = "flow" + str(day)
        # print(field_day, field_flow)

        field = "ip," + field_day + ' as day,' + field_flow + " as flow"

        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))

    elif query_date == "yesterday":

        ftime = time.localtime(time.time() - 86400)
        day = ftime.tm_mday

        field_day = "day" + str(day)
        field_flow = "flow" + str(day)

        field = "ip," + field_day + ' as day,' + field_flow + " as flow"

        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))
    elif query_date == "l7":

        field_day = ""
        field_flow = ""

        now_time = time.localtime(time.time())
        end_day = now_time.tm_mday

        start_time = time.localtime(time.time() - 7 * 86400)
        start_day = start_time.tm_mday

        rlist = getDateRangeList(start_day, end_day)

        for x in rlist:
            field_day += "+cast(day" + str(x) + " as TEXT)"
            field_flow += "+cast(flow" + str(x) + " as TEXT)"

        field_day = field_day.strip("+")
        field_flow = field_flow.strip("+")

        field = "ip,(" + field_day + ') as day,(' + field_flow + ") as flow"
        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))

    elif query_date == "l30":

        field_day = ""
        field_flow = ""

        for x in list(range(1, 32, 1)):
            field_day += "+cast(day" + str(x) + " as TEXT)"
            field_flow += "+cast(flow" + str(x) + " as TEXT)"

        field_day = field_day.strip("+")
        field_flow = field_flow.strip("+")

        # print(field_day)
        # print(field_flow)
        field = "ip,(" + field_day + ') as day,(' + field_flow + ") as flow"
        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))

    clist = conn.order("flow desc").limit("50").inquiry(origin_field)
    # print(clist)

    total_req = 0
    total_flow = 0

    gepip_mmdb = getServerDir() + '/GeoLite2-City.mmdb'
    geoip_exists = False
    if os.path.exists(gepip_mmdb):
        import geoip2.database
        reader = geoip2.database.Reader(gepip_mmdb)
        geoip_exists = True
        # response = reader.city("172.70.206.144")
        # print(response.country.names["zh-CN"])
        # print(response.subdivisions.most_specific.names["zh-CN"])
        # print(response.city.names["zh-CN"])

    for x in clist:
        total_req += x['day']
        total_flow += x['flow']

    for i in range(len(clist)):
        clist[i]['day_rate'] = round((clist[i]['day'] / total_req) * 100, 2)
        clist[i]['flow_rate'] = round((clist[i]['flow'] / total_flow) * 100, 2)
        ip = clist[i]['ip']

        if ip == "127.0.0.1":
            clist[i]['area'] = "本地"
        elif geoip_exists:
            try:
                response = reader.city(ip)
                country = response.country.names["zh-CN"]

                # print(ip, response.subdivisions)
                _subdivisions = response.subdivisions
                try:
                    if len(_subdivisions) < 1:
                        subdivisions = ""
                    else:
                        subdivisions = "," + response.subdivisions.most_specific.names[
                            "zh-CN"]
                except Exception as e:
                    subdivisions = ""

                try:
                    if 'zh-CN' in response.city.names:
                        city = "," + response.city.names["zh-CN"]
                    else:
                        city = "," + response.city.names["en"]
                except Exception as e:
                    city = ""

                clist[i]['area'] = country + subdivisions + city
            except Exception as e:
                clist[i]['area'] = "内网?"

    return mw.returnJson(True, 'ok', clist)


def getUriStatList():
    args = getArgs()
    check = checkArgs(args, ['site', 'query_date'])
    if not check[0]:
        return check[1]

    domain = args['site']
    tojs = args['tojs']
    query_date = args['query_date']
    setDefaultSite(domain)

    conn = pSqliteDb('uri_stat', domain)

    origin_field = "uri,day,flow"

    if query_date == "today":
        ftime = time.localtime(time.time())
        day = ftime.tm_mday

        field_day = "day" + str(day)
        field_flow = "flow" + str(day)
        # print(field_day, field_flow)

        field = "uri," + field_day + ' as day,' + field_flow + " as flow"

        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))

    elif query_date == "yesterday":

        ftime = time.localtime(time.time() - 86400)
        day = ftime.tm_mday

        field_day = "day" + str(day)
        field_flow = "flow" + str(day)

        field = "uri," + field_day + ' as day,' + field_flow + " as flow"

        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))
    elif query_date == "l7":

        field_day = ""
        field_flow = ""

        now_time = time.localtime(time.time())
        end_day = now_time.tm_mday

        start_time = time.localtime(time.time() - 7 * 86400)
        start_day = start_time.tm_mday

        rlist = getDateRangeList(start_day, end_day)

        for x in rlist:
            field_day += "+cast(day" + str(x) + " as TEXT)"
            field_flow += "+cast(flow" + str(x) + " as TEXT)"

        field_day = field_day.strip("+")
        field_flow = field_flow.strip("+")

        field = "uri,(" + field_day + ') as day,(' + field_flow + ") as flow"
        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))

    elif query_date == "l30":

        field_day = ""
        field_flow = ""

        for x in list(range(1, 32, 1)):
            field_day += "+cast(day" + str(x) + " as TEXT)"
            field_flow += "+cast(flow" + str(x) + " as TEXT)"

        field_day = field_day.strip("+")
        field_flow = field_flow.strip("+")

        # print(field_day)
        # print(field_flow)
        field = "uri,(" + field_day + ') as day,(' + field_flow + ") as flow"
        conn = conn.field(field)
        conn = conn.where("day>? and flow>?", (0, 0,))

    clist = conn.order("flow desc").limit("50").inquiry(origin_field)

    total_req = 0
    total_flow = 0

    for x in clist:
        total_req += x['day']
        total_flow += x['flow']

    for i in range(len(clist)):
        clist[i]['day_rate'] = round((clist[i]['day'] / total_req) * 100, 2)
        clist[i]['flow_rate'] = round((clist[i]['flow'] / total_flow) * 100, 2)

    return mw.returnJson(True, 'ok', clist)


def getWebLogCount(domain, query_date):
    conn = pSqliteDb('web_logs', domain)

    todayTime = time.strftime('%Y-%m-%d 00:00:00', time.localtime())
    todayUt = int(time.mktime(time.strptime(todayTime, "%Y-%m-%d %H:%M:%S")))
    if query_date == 'today':
        conn = conn.where("time>=?", (todayUt,))
    elif query_date == "yesterday":
        conn = conn.where("time>=? and time<=?", (todayUt - 86400, todayUt))
    elif query_date == "l7":
        conn = conn.where("time>=?", (todayUt - 7 * 86400,))
    elif query_date == "l30":
        conn = conn.where("time>=?", (todayUt - 30 * 86400,))
    else:
        exlist = query_date.split("-")
        conn = conn.where("time>=? and time<=?", (exlist[0], exlist[1]))

    count_key = "count(*) as num"
    count = conn.field(count_key).limit('').order('').inquiry()
    count = count[0][count_key]
    return count


def getSpiderStatList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'query_date'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    query_date = args['query_date']
    setDefaultSite(domain)

    conn = pSqliteDb('spider_stat', domain)
    stat = pSqliteDb('spider_stat', domain)

    total_req = getWebLogCount(domain, query_date)

    # 列表
    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    field = 'time,bytes,bing,soso,yahoo,sogou,google,baidu,qh360,youdao,yandex,dnspod,other'
    field_sum = toSumField(field.replace("time,", ""))
    time_field = "substr(time,1,8),"
    field_sum = time_field + field_sum

    stat = stat.field(field_sum)
    if query_date == "today":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 0 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "yesterday":
        startTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 1 * 86400))
        endTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time()))
        stat.where("time>=? and time<=?", (startTime, endTime))
    elif query_date == "l7":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 7 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "l30":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 30 * 86400))
        stat.where("time >= ?", (todayTime,))
    else:
        exlist = query_date.split("-")
        start = time.strftime(
            '%Y%m%d00', time.localtime(int(exlist[0])))
        end = time.strftime(
            '%Y%m%d23', time.localtime(int(exlist[1])))
        stat.where("time >= ? and time <= ? ", (start, end,))

    # 图表数据
    statlist = stat.group('substr(time,1,4)').inquiry(field)

    if len(statlist) > 0:
        del(statlist[0]['time'])

        spider_total = 0
        for x in statlist[0]:
            spider_total += statlist[0][x]

        sum_data = {"spider": spider_total, "reqest_total": total_req}
        statlist = sorted(statlist[0].items(),
                          key=lambda x: x[1], reverse=True)
        _statlist = statlist[0:9]
        __statlist = {}
        statlist = []
        for x in _statlist:
            __statlist[x[0]] = x[1]
        statlist.append(__statlist)
    else:
        sum_data = {"spider": 0, "reqest_total": total_req}
        statlist = []

    # 列表数据
    conn = conn.field(field_sum)
    clist = conn.group('substr(time,1,8)').limit(
        limit).order('time desc').inquiry(field)

    sql = "SELECT count(*) num from (\
            SELECT count(*) as num FROM spider_stat GROUP BY substr(time,1,8)\
        )"
    result = conn.query(sql, ())
    result = list(result)
    count = result[0][0]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist
    data['stat_list'] = statlist
    data['sum_data'] = sum_data

    return mw.returnJson(True, 'ok', data)


def installPreInspection():
    check_op = mw.getServerDir() + "/openresty"
    if not os.path.exists(check_op):
        return "请先安装OpenResty"
    return 'ok'

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'install_pre_inspection':
        print(installPreInspection())
    elif func == 'run_info':
        print(runInfo())
    elif func == 'get_global_conf':
        print(getGlobalConf())
    elif func == 'set_global_conf':
        print(setGlobalConf())
    elif func == 'get_site_conf':
        print(getSiteConf())
    elif func == 'set_site_conf':
        print(setSiteConf())
    elif func == 'get_default_site':
        print(getDefaultSite())
    elif func == 'get_overview_list':
        print(getOverviewList())
    elif func == 'get_site_list':
        print(getSiteList())
    elif func == 'get_logs_list':
        print(getLogsList())
    elif func == 'get_logs_error_list':
        print(getLogsErrorList())
    elif func == 'get_logs_realtime_info':
        print(getLogsRealtimeInfo())
    elif func == 'get_client_stat_list':
        print(getClientStatList())
    elif func == 'get_ip_stat_list':
        print(getIpStatList())
    elif func == 'get_uri_stat_list':
        print(getUriStatList())
    elif func == 'get_spider_stat_list':
        print(getSpiderStatList())
    else:
        print('error')
