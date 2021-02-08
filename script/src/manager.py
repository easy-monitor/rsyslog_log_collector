#!/usr/local/easyops/python/bin/python
# _*_coding: utf-8_*_

import json
import os
import logging
import random
import logging.handlers
import traceback
import time

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
app_name = os.environ.get("EASYOPS_COLLECTOR_app_name", "")

business_id = os.environ.get("EASYOPS_COLLECTOR_business_id")
business_name = os.environ.get("EASYOPS_COLLECTOR_business_name", "")

host_ip = os.environ.get("EASYOPS_COLLECTOR_host_ip")
expire_time = os.environ.get("EASYOPS_COLLECTOR_expire_time", 60)
log_type = os.environ.get("EASYOPS_COLLECTOR_log_type", "")


file_prefix = u"easyops_rsyslog_job_conf_{}"

rsyslog_conf_tpl = u'''
$ModLoad imfile
$WorkDirectory  {work_dir}
$InputFileName  {collect_file}
$InputFileTag {input_tag}
$InputFileStateFile  {rsyslog_file_state_file}
$InputFileSeverity info 
$InputRunFileMonitor

$template {template_name}, "<%PRI%>1 %TIMESTAMP:::date-rfc3339% %HOSTNAME% %APP-NAME% - %MSGID% [meta@easyops host=\\"{host_ip}\\" business_id=\\"{business_id}\\" business=\\"{business_name}\\" app=\\"{app_name}\\" app_id=\\"{app_id}\\" log_type=\\"{log_type}\\" log_file_path=\\"{collect_file}\\"] %msg%\\n"

if $programname == '{input_tag}' then  @@{easyops_server_ip}:{easyops_server_port};{template_name}
& ~
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


def generate_conf(server_ip, one_file, work_dir):
    try:
        tag = "{}-{}".format(common.get_job_id_from_path(), common.get_md5(one_file))
        rsyslog_conf = rsyslog_conf_tpl.format(
            work_dir=work_dir,
            collect_file=one_file,
            input_tag=tag,
            template_name=tag,
            rsyslog_file_state_file=os.path.join(work_dir, "state"),
            easyops_server_ip=server_ip,
            easyops_server_port=easyops_server_port,
            business_id=business_id,
            business_name=business_name.decode("utf-8"),
            app_name=app_name.decode("utf-8"),
            app_id=app_id,
            host_ip=host_ip,
            log_type=log_type.decode("utf-8"),
        )
        return rsyslog_conf
    except Exception as e:
        logging.error(traceback.format_exc())
        raise e


def check_conf_change(conf_map):
    last_conf_md5_map = common.get_last_conf_md5(
        common.get_record_file_path(
            common.get_md5(collect_file)
        )
    )

    logging.info(last_conf_md5_map)
    to_add = {}
    conf_md5_map = {}
    for file_name, conf in conf_map.iteritems():
        conf_md5_map[file_name] = common.get_md5(conf)
        if file_name in last_conf_md5_map:
            if last_conf_md5_map[file_name] == conf_md5_map[file_name]:
                del last_conf_md5_map[file_name]
                logging.info(u"file %s conf not change", file_name)
            else:
                to_add[file_name] = conf_md5_map[file_name]
        else:
            to_add[file_name] = conf_md5_map[file_name]

    return conf_md5_map, to_add, last_conf_md5_map


def run():
    common.log_setup()
    common.check_record_file_path()
    if not collect_file:
        logging.error("get invalid collect_file, %s", collect_file)
        return

    # IP为空则从配置文件获取
    server_ip = random.choice(common.get_server_ip(easyops_server_ip))
    conf_map = {}
    work_dir = os.path.join(common.BASE_PATH, "work_dir")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir, 0755)

    for file_name in collect_file.split(","):
        conf_map[file_name] = generate_conf(server_ip, file_name, work_dir)

    total_conf, new_conf, expire_conf = check_conf_change(conf_map)

    # record conf to file
    common.record_conf_file(common.get_record_conf(
        total_conf,
        job_id,
        rsyslog_conf_path,
        restart_cmd,
        ), common.get_record_file_path(
            common.get_md5(collect_file)
        )
    )

    if not new_conf and not expire_conf:
        logging.info(u"nothing change, end here")
        return "remain"

    try:
        logging.info(u'start generate conf')
        for file_name in new_conf:
            conf_name = file_prefix.format(total_conf[file_name])
            common.write_conf(conf_map[file_name].encode("utf-8"), conf_name)

            conf_file_path = common.get_conf_file_path(conf_name)
            logging.info(u"link %s", conf_file_path)
            link_conf(conf_file_path,
                      os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name)))

        for file_name, md5 in expire_conf.iteritems():
            conf_name = file_prefix.format(md5)
            conf_file_path = os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name))
            logging.info(u"unlink %s", conf_file_path)
            unlink_conf(conf_file_path)

        restart_rsyslog(restart_cmd)
        logging.info(u'end generate conf')
        return "update"
    except Exception as e:
        logging.error(traceback.format_exc())
        raise e


def output_result(rsyslog_operate_type=""):
    print json.dumps([{
        'dims': {},
        'vals': {
            "rsyslog_operate_type": rsyslog_operate_type
        }
    }])


def check_expire_conf(expire_time=300):
    all_record_file = common.get_all_record_file()
    for file_name in all_record_file:
        now, mtime = int(time.time()), int(common.get_file_mtime(file_name))
        if now - mtime > expire_time:
            logging.info("file %s mtime %d now %d, will clean rsyslog conf file", file_name, mtime, now)
            conf_record = common.load_conf_file(file_name)

            for collect_file_name, md5 in conf_record.get(common.RSYSLOG_CONF_MD5_KEY, {}).iteritems():
                conf_name = file_prefix.format(md5)
                conf_file_path = os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name))
                unlink_conf(conf_file_path)
                logging.info(u"unlink %s", conf_file_path)
                os.remove(file_name)
                logging.info("remove file %s", file_name)
        else:
            logging.info("file %s mtime %d not expire", file_name, mtime)


if __name__ == "__main__":
    try:
        operate_type = run()
        output_result(operate_type)
        check_expire_conf(expire_time*5)
    except Exception as e:
        logging.error(e.message)
        logging.error(traceback.format_exc())
