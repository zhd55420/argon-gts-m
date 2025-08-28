import os
import datetime
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
import pytz
import django
import apps
# 配置 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')




django.setup()

from apps.myapp.Utils.send_to_lark import send_message_to_optlark, send_message_to_spclark,send_message_to_streamlark,send_message_to_Vodlark
from apps.myapp.Utils.query_bandwidth import query_and_log_bandwidth,query_and_log_tracker_users,query_and_log_resource_groups,query_and_log_vod  # 确保函数被正确导入
from apps.myapp.Utils.send_to_zabbix import query_vod_bw_users_send_to_zabbix,query_bw_users_send_to_zabbix
from apps.myapp.Utils.send_streamstatus_to_influxdb import all_stream_task,all_goose_stream_task,all_goose_stream_tasks2


def run_opt_job_users_and_bw():
    query_and_log_bandwidth("opt", send_message_to_optlark)


def run_spc_job_users_and_bw():
    query_and_log_bandwidth("spc", send_message_to_spclark)

def run_spc_tracker_job_users():
    query_and_log_tracker_users("spc", send_message_to_spclark)

def run_resource_group_job():
    query_and_log_resource_groups(send_message_to_streamlark)

def run_vod_job_users_and_bw():
    query_and_log_vod(send_message_to_Vodlark)

def send_data_to_live_zabbix():
    query_bw_users_send_to_zabbix('opt')
    query_bw_users_send_to_zabbix('spc')

def send_data_to_vod_zabbix():
    query_vod_bw_users_send_to_zabbix()

def send_stream_status_influxdb():
    all_stream_task()
    all_goose_stream_task()
    all_goose_stream_tasks2()

if __name__ == '__main__':
    send_stream_status_influxdb()



