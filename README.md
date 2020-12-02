# EasyOps rsyslog 监控插件包

EasyOps rsyslog 监控插件包是适用于 EasyOps 新版监控平台，适用于 应用日志采集 功能。能生成，管理rsyslog 配置，用于统一收集日志内容到服务端。

## 目录

- [适用环境](#适用环境)
- [工作原理](#工作原理)
- [准备工作](#准备工作)
- [使用方法](#使用方法)
- [项目内容](#项目内容)
- [许可证](#许可证)

## 适用环境

`redhat   6, 7`

`rsyslog  5.8.10,  8.24.0-34.el7`

## 工作原理

1. 根据提供到文件路径，配置路径等参数，生成配置文件，并软链到 `rsyslog` 配置目录，重启 `rsyslog`。

## 准备工作

1. 确认`rsyslog`配置文件路径、重启命令。
2. 确认 agent 到服务器 8825 端口通信可达。

## 使用方法

### 导入监控插件包

1. 下载该项目的压缩包。

2. 建议解压到 EasyOps 平台服务器上的 `/data/easyops/monitor_plugin_packages` 目录下。

3. 使用 EasyOps 平台提供的自动化工具一键导入该插件包，具体命令如下，请替换其中的 `8888` 为当前 EasyOps 平台具体的 `org`。

```sh
$ cd /usr/local/easyops/collector_plugin_service/tools
$ sh plugin_op.sh install 8888 /data/easyops/monitor_plugin_packages/easyops_rsyslog_log_collector
```

4. 导入成功后访问 EasyOps 平台的「采集插件」列表页面 ( http://your-easyops-server/next/collector-plugin )，就能看到导入的 "easyops_rsyslog_collector" 采集插件。

## 项目内容

### 目录结构

```
easyops_rsyslog_log_collector
├── dashboard.json
├── origin_metric.json
└── script
    ├── package.conf.yaml
    ├── plugin.yaml
    └── src
        ├── log
        ├── manager.py
        └── util
            ├── __init__.py
            ├── cmd_util.py
            ├── common.py
├── tools
    └── stop.py 
```

该项目的目录结构遵循标准的 EasyOps 监控插件包规范，具体内容如下：

- dashboard.json: 仪表盘的定义文件
- origin_metric.json: 采集插件关联的监控指标定义文件
- script: 采集插件关联的程序包目录，执行采集任务时会部署到指定的目标机器上
- script/log: 日志文件目录
- script/package.conf.yaml: 采集插件关联的程序包的定义文件
- script/plugin.yaml: 采集插件包的定义文件
- script/src: 主逻辑代码目录

### plugin.yaml

```yaml
# 支持 easyops/prometheus/zabbix-agent 三种采集类型
# 1. easyops: 表示使用 EasyOps Agent 进行指标采集
# 2. prometheus: 表示对接 Prometheus Exporter 进行指标采集
# 3. zabbix-agent: 表示对接 Zabbix Agent 进行指标采集
agentType: prometheus

# 采集插件的名称，也是采集插件关联的程序包名称
name: easyops_rsyslog_collector
# 采集插件关联的程序包版本名称
version: 1.0.0

# 采集插件类别 
category: OS系统
# 采集插件参数列表
params:
    - restart_cmd
    - collect_file
    - job_id
    - rsyslog_conf_path
    - easyops_server_ip
    - easyops_server_port
    - app_id
    - business_id
    - business_name
    - host_ip
```

## 许可证

[MIT](#许可证) © EasyOps
