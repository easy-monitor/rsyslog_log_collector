#!/usr/local/easyops/python/bin/python
# _*_coding: utf-8_*_

import yaml
import os
import logging
import random
import logging.handlers
import yaml
import traceback

# pro
from util import common, cmd_util

restart_cmd = os.environ.get("EASYOPS_COLLECTOR_restart_cmd")
# collect_interval = os.environ.get("EASYOPS_COLLECTOR_collect_interval")
collect_file = os.environ.get("EASYOPS_COLLECTOR_collect_file")
job_id = os.environ.get("EASYOPS_COLLECTOR_job_id")
# intput_tag = os.environ.get("EASYOPS_COLLECTOR_intput_tag")
rsyslog_conf_path = os.environ.get("EASYOPS_COLLECTOR_rsyslog_conf_path")

easyops_server_ip = os.environ.get("EASYOPS_COLLECTOR_easyops_server_ip")
easyops_server_port = os.environ.get("EASYOPS_COLLECTOR_easyops_server_port")
app_id = os.environ.get("EASYOPS_COLLECTOR_app_id")
business_id = os.environ.get("EASYOPS_COLLECTOR_business_id")
host_ip = os.environ.get("EASYOPS_COLLECTOR_host_ip")

file_prefix = u"easyops_rsyslog_job_conf_{}"

rsyslog_conf_tpl = u'''
module(load="imfile")

input(type="imfile"
    File="{collect_file}"
    Tag="{input_tag}"
    Ruleset="sendToLogSer_{input_tag}"
    addMetadata="on")

template(name="{template_name}" type="list") {{
    constant(value="{{\\"")

    constant(value="host")
    constant(value="\\": \\"")
    constant(value="{host_ip}")
    constant(value="\\", \\"")

    constant(value="business_id")
    constant(value="\\": \\"")
    constant(value="{business_id}")
    constant(value="\\", \\"")

    constant(value="app_id")
    constant(value="\\": \\"")
    constant(value="{app_id}")
    constant(value="\\", \\"")

    constant(value="log_file_path")
    constant(value="\\": \\"")
    property(name="$!metadata!filename")
    constant(value="\\", \\"")

    constant(value="message")
    constant(value="\\": \\"")
    property(name="msg")
    constant(value="\\"")
    constant(value="}}")
    }}

ruleset(name="sendToLogSer_{input_tag}") {{
    action(type="omfwd"
           target="{easyops_server_ip}"
           port="{easyops_server_port}"
           protocol="tcp"
           template="{template_name}"
           queue.type="LinkedList" 
           queue.size="10000"
           queue.filename="q_{input_tag}"
           queue.highwatermark="9000"
           queue.lowwatermark="50"
           queue.maxdiskspace="500m"
           queue.saveonshutdown="on" 
           action.resumeRetryCount="-1"
           action.reportSuspension="on"
           action.reportSuspensionContinuation="on"
           action.resumeInterval="10")
    stop
}}
'''


def link_conf(src_file, dst_file):
    rcode, output = cmd_util.run_cmd(u"ln -sf {} {}".format(src_file, dst_file), shell=True)


def unlink_conf(dst_file):
    return cmd_util.run_cmd(u"rm -f {}".format(dst_file), shell=True)


def restart_rsyslog(cmd="service rsyslog restart"):
    logging.info(u'restrat rsyslog, cmd is %s', cmd)
    rcode, output = cmd_util.run_cmd(cmd, shell=True)
    logging.info(u"restart complete, rcode=%s, output=%s", rcode, output)
    return


def generate_conf(server_ip, one_file):
    try:
        job_id = common.get_job_id_from_path()
        rsyslog_conf = rsyslog_conf_tpl.format(
            collect_file=one_file,
            input_tag=job_id,
            template_name=job_id,
            easyops_server_ip=server_ip,
            easyops_server_port=easyops_server_port,
            business_id=business_id,
            app_id=app_id,
            host_ip=host_ip,
        )
        return rsyslog_conf
    except Exception as e:
        logging.error(traceback.format_exc())
        raise e


def check_conf_change(conf_map):
    last_conf_md5_map = common.get_last_conf_md5()
    logging.info(last_conf_md5_map)

    to_add = []

    conf_md5_map = {}
    for file_name, conf in conf_map.iteritems():
        conf_md5_map[file_name] = common.get_md5(conf)
        if file_name in last_conf_md5_map:
            if last_conf_md5_map[file_name] == conf_md5_map[file_name]:
                del last_conf_md5_map[file_name]
                logging.info(u"file %s conf not change", file_name)
            else:
                to_add.append(file_name)
        else:
            to_add.append(file_name)

    return conf_md5_map, to_add, last_conf_md5_map.keys()


def run():
    common.log_setup()
    # IP为空则从配置文件获取
    server_ip = random.choice(common.get_server_ip(easyops_server_ip))
    conf_map = {}
    for file_name in collect_file.split(","):
        conf_map[file_name] = generate_conf(server_ip, file_name)

    #  dict       list       list
    total_conf, new_conf, expire_conf = check_conf_change(conf_map)
    if not new_conf and not expire_conf:
        logging.info(u"nothing change, end here")
        return

    # record conf to file
    common.record_conf_file(common.get_record_conf(
        total_conf,
        job_id,
        rsyslog_conf_path,
        restart_cmd,
    ))

    try:
        logging.info(u'start generate conf')
        for file_name in new_conf:
            conf_name = file_prefix.format(total_conf[file_name])
            common.write_conf(conf_map[file_name].encode("utf-8"), conf_name)

            conf_file_path = common.get_conf_file_path(conf_name)
            logging.info(u"link %s", conf_file_path)
            link_conf(conf_file_path,
                      os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name)))

        for file_name in expire_conf:
            conf_name = file_prefix.format(total_conf[file_name])
            conf_file_path = common.get_conf_file_path(conf_name)
            logging.info(u"unlink %s", conf_file_path)
            unlink_conf(conf_file_path)

        restart_rsyslog(restart_cmd)
        logging.info(u'end generate conf')
    except Exception as e:
        logging.error(traceback.format_exc())
        raise e


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(e.message)
        logging.error(traceback.format_exc())
