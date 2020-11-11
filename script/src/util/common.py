#!/usr/local/easyops/python/bin/python
# _*_coding: utf-8_*_


import logging
import yaml
import os
import hashlib

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF_PATH = os.path.join(BASE_PATH, "rsyslog_conf")

RSYSLOG_CONF_MD5_KEY = "rsyslog_conf_md5_map"

EAYSOPS_PATH = os.environ.get("EASYOPS_BASE_PATH", "")
if EAYSOPS_PATH == "":
    EAYSOPS_PATH = "/usr/local/easyops"

log_file_path = os.path.join(BASE_PATH, "log")
if not os.path.exists(log_file_path):
    os.mkdir(log_file_path)


def get_md5(content):
    hl = hashlib.md5()
    hl.update(content.encode(encoding='utf-8'))
    return hl.hexdigest()


def get_ip_from_agent_conf():
    agent_conf_file = os.path.join(EAYSOPS_PATH, "agent", "conf", "conf.yaml")
    ips = []
    try:
        with open(agent_conf_file, "r") as f:
            conf = yaml.load(f.read())
            host_gourp = [group["hosts"] for group in
                          [server_groups for server_groups in conf["report"]["server_groups"]]]
            for hosts in host_gourp:
                for host in hosts:
                    ips.extend(host["ip"].split(","))
        logging.info("get server_ip form conf file")
        return ips
    except Exception as e:
        raise


def get_server_ip(server_ip):
    if server_ip == "":
        server_ip = get_ip_from_agent_conf()

    if not isinstance(server_ip, (list, set)):
        server_ip = [server_ip]
    logging.info("get server_ip %s", server_ip)
    return server_ip


def log_setup():
    log_handler = logging.handlers.WatchedFileHandler(os.path.join(log_file_path, 'conf_op.log'))
    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    # formatter.converter = time.gmtime  # if you want UTC time
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def get_last_conf_md5():
    return load_conf_file().get(RSYSLOG_CONF_MD5_KEY, {})


def load_conf_file(conf_record_file="job_conf.ini"):
    try:
        with open(os.path.join(BASE_PATH, conf_record_file), "r") as f:
            content = f.read()
            conf = yaml.load(content)
            logging.info("get conf file %s", content)
            return conf
    except Exception as e:
        logging.error("load conf file %s error,msg=%s", conf_record_file, e.message)
        return {}


def record_conf_file(conf, conf_record_file="job_conf.ini"):
    with open(os.path.join(BASE_PATH, conf_record_file), "w") as f:
        yaml.dump(conf, f)
    logging.info("record conf %s to file %s", conf, conf_record_file)


def get_record_conf(md5, collector_name, rsyslog_conf_path, restart_cmd):
    return {
        RSYSLOG_CONF_MD5_KEY: md5,
        "job_id": collector_name,
        "rsyslog_conf_path": rsyslog_conf_path,
        "restart_cmd": restart_cmd,
    }


def get_conf_file_name(name):
    return name + ".conf"


def get_conf_file_path(name):
    return os.path.join(CONF_PATH, get_conf_file_name(name))


def write_conf(conf, name):
    output_path = get_conf_file_path(name)
    if not os.path.exists(CONF_PATH):
        os.makedirs(CONF_PATH)
    with open(output_path, "w") as f:
        f.write(conf)
    logging.info("write conf to %s complete", output_path)


def get_job_id_from_path():
    return os.path.dirname(BASE_PATH).rsplit("/", 1)[-1].split("-", 1)[-1]
