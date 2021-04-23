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
from util import common, cmd_util, lock


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
message_size = os.environ.get("EASYOPS_COLLECTOR_message_size", "64k")

file_prefix = u"easyops_rsyslog_job_conf_{}_{}"
lock_file = os.path.join(common.PLUGIN_PATH, ".rsyslog_op.lock")

rsyslog_conf_tpl = u'''
$ModLoad imfile
$InputFileName  {collect_file}
$InputFileTag {input_tag}
$InputFileSeverity info 
$InputRunFileMonitor
$MaxMessageSize {message_size}

$template {template_name}, "<%PRI%>1 %TIMESTAMP:::date-rfc3339% %HOSTNAME% %APP-NAME% - %MSGID% [meta@easyops host=\\"{host_ip}\\" business_id=\\"{business_id}\\" business=\\"{business_name}\\" app=\\"{app_name}\\" app_id=\\"{app_id}\\" log_type=\\"{log_type}\\" log_file_path=\\"{collect_file}\\"] %msg%\\n"

if $programname == '{input_tag}' then  @@{easyops_server_ip}:{easyops_server_port};{template_name}
& ~
'''
lock.create_lock_file(lock_file)


def link_conf(src_file, dst_file):
    rcode, output = cmd_util.run_cmd(u"ln -sf {} {}".format(src_file, dst_file), shell=True)


def unlink_conf(dst_file):
    return cmd_util.run_cmd(u"rm -f {}".format(dst_file), shell=True)


@lock.run_with_filelock(lock_file)
def restart_rsyslog(cmd="service rsyslog restart", *args, **kwargs):
    logging.info(u'restrat rsyslog, cmd is %s', cmd)
    rcode, output = cmd_util.run_cmd(cmd, shell=True)
    logging.info(u"restart complete, rcode=%s, output=%s", rcode, output)
    return


def kill_all_rsyslog():
    cmd = " ps -fC rsyslogd | grep -v 'grep' | grep -v 'next_collector_plugins' | awk '{print $2}' | xargs kill "
    return cmd_util.run_cmd(cmd, shell=True)


def check_rsyslog_proc_num():
    cmd = " ps -fC rsyslogd | grep -v 'grep' | grep -v 'next_collector_plugins' "
    return cmd_util.run_cmd(cmd, shell=True)


def generate_conf(server_ips, one_file):
    conf_map = {}
    for ip in server_ips:
        try:
            tag = "{}-{}".format(common.get_job_id_from_path(), common.get_md5(one_file))
            conf_map[ip] = rsyslog_conf_tpl.format(
                collect_file=one_file,
                input_tag=tag,
                template_name=tag,
                easyops_server_ip=ip,
                easyops_server_port=easyops_server_port,
                business_id=business_id,
                business_name=business_name.decode("utf-8"),
                app_name=app_name.decode("utf-8"),
                app_id=app_id,
                host_ip=host_ip,
                log_type=log_type.decode("utf-8"),
                message_size=message_size,
            )

        except Exception as e:
            logging.error(traceback.format_exc(), e.message)
    return conf_map


# 每个文件按collector proxy的多个IP生成多个配置， 最终效果为只有真正配置有变动的情况下会重新生成配置，而随机选择上报IP不会。
def check_conf_change(conf_map):
    def check_one_file(file_name, cur_conf, last_conf):
        all_conf = {}
        add_conf = {}
        for ip, conf in cur_conf.iteritems():
            all_conf[ip] = common.get_md5(conf)

            if ip in last_conf:
                if last_conf[ip] == all_conf[ip]:
                    del last_conf[ip]
                    logging.info(u"file %s ip %s conf not change", file_name, ip)
                else:
                    add_conf[ip] = all_conf[ip]
            else:
                add_conf[ip] = all_conf[ip]
        return all_conf, add_conf, last_conf

    last_conf_md5_map = common.get_last_conf_md5(
        common.get_record_file_path(
            common.get_md5(collect_file)
        )
    )

    logging.info(last_conf_md5_map)
    total_conf, to_add, to_del = {}, {}, {}
    for file_name, conf_in_ips in conf_map.iteritems():
        total_conf[file_name], to_add_each, to_del_each = check_one_file(file_name, conf_in_ips, last_conf_md5_map.get(file_name, {}))
        if to_add_each:
            to_add[file_name] = to_add_each
        if to_del_each:
            to_add[file_name] = to_del_each
    return total_conf, to_add, to_del


def run():
    common.log_setup()
    common.check_record_file_path()

    if not collect_file:
        logging.error("get invalid collect_file, %s", collect_file)
        return

    # IP为空则从配置文件获取
    server_ips = common.get_server_ip(easyops_server_ip)

    conf_map = {}
    work_dir = os.path.join(common.BASE_PATH, "work_dir")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir, 0755)

    # rsyslog 配置map
    for file_name in collect_file.split(","):
        conf_map[file_name] = generate_conf(server_ips, file_name)

    # rsyslog 配置md5 map
    total_conf, new_conf, expire_conf = check_conf_change(conf_map)

    # record conf to file
    common.record_conf_file(common.get_record_conf(
        total_conf,
        job_id or common.get_job_id_from_path(),
        rsyslog_conf_path,
        restart_cmd,
        ),
        common.get_record_file_path(
            common.get_md5(collect_file)
        )
    )

    if not new_conf and not expire_conf:
        logging.info(u"nothing change, will start check ln file")

        # 检查并补齐ln
        for file_name, confs in total_conf.iteritems():
            conf_name = file_prefix.format(job_id or common.get_job_id_from_path(), common.get_md5(file_name))
            ln_file = os.path.join(rsyslog_conf_path,  common.get_conf_file_name(conf_name))
            logging.info("check ln file %s", ln_file)
            # 目标软链文件不存在，则重新生成
            if not os.path.exists(ln_file):
                logging.info("check ln file %s not exist, will regen ln", ln_file)
                # 选取第一个IP后就break，相当于随机选一个
                for ip, md5 in confs.iteritems():
                    gen_ln_conf(conf_map[file_name][ip].encode("utf-8"), conf_name)
                    break
            else:
                logging.info("ln file %s exist", ln_file)

        return "remain"

    try:
        logging.info(u'start generate conf')
        logging.debug(expire_conf)
        logging.debug(new_conf)

        # 选取第一个IP后就break，相当于随机选一个
        for file_name, confs in new_conf.iteritems():
            logging.info("get change conf with file_name %s", file_name)
            for ip, md5 in confs.iteritems():
                logging.info("choice first ip is %s", ip)
                conf_name = file_prefix.format(common.get_job_id_from_path(), common.get_md5(file_name))
                gen_ln_conf(conf_map[file_name][ip].encode("utf-8"), conf_name)
                break

        for file_name, confs in expire_conf.iteritems():
            logging.info("get expire conf with file_name %s, will delete", file_name)

            for ip, md5 in confs.iteritems():
                conf_name = file_prefix.format(md5)
                conf_file_path = os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name))
                logging.info(u"unlink %s", conf_file_path)
                unlink_conf(conf_file_path)

        restart_rsyslog(restart_cmd)
        time.sleep(1)

        logging.info("start check proc num")
        returncode, result = check_rsyslog_proc_num()
        if returncode:
            logging.error("check proc num error %s", result)
        else:
            logging.info("check proc result %s", result)
            try:
                proc_num = result.splitlines()
                if len(proc_num) > 1:
                    logging.info("proc num %s > 1, will kill rsyslog process", len(proc_num))
                    kill_all_rsyslog()

                    logging.info("proc num %s > 1, will restart again", len(proc_num))
                    restart_rsyslog(restart_cmd)
                else:
                    logging.info("proc num check ok")
            except Exception as e:
                logging.error("result convert int error, %s", e.message)

        logging.info(u'end generate conf')
        return "update"
    except Exception as e:
        logging.error(traceback.format_exc())
        raise e


def gen_ln_conf(content, conf_name):
    common.write_conf(content, conf_name)

    conf_file_path = common.get_conf_file_path(conf_name)
    logging.info(u"link %s", conf_file_path)
    link_conf(conf_file_path, os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name)))


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
            check_expire_one_file(conf_record)
            os.remove(file_name)
            logging.info("remove file %s", file_name)
        else:
            logging.info("file %s mtime %d not expire", file_name, mtime)


def check_expire_one_file(conf_record):
    for collect_file_name, confs in conf_record.get(common.RSYSLOG_CONF_MD5_KEY, {}).iteritems():
        for ip, md5 in confs.iteritems():
            conf_name = file_prefix.format(md5)
            conf_file_path = os.path.join(rsyslog_conf_path, common.get_conf_file_name(conf_name))
            unlink_conf(conf_file_path)
            logging.info(u"unlink %s", conf_file_path)


if __name__ == "__main__":
    try:
        operate_type = run()
        output_result(operate_type)
        check_expire_conf(expire_time*5)
    except Exception as e:
        logging.error(e.message)
        logging.error(traceback.format_exc())
