import logging
from pyzabbix import ZabbixMetric, ZabbixSender
from django.conf import settings
from apps.myapp.Utils.get_influxdb_client import get_livetv_influxdb_client, get_vod_influxdb_client
from apps.myapp.Utils.get_brand_users_bw import InfluxDBQueryTool
from apps.myapp.Utils.convert_cfg import load_config
from apps.myapp.Utils.get_vod_users_bw import VodQueryTool

# 获取 Zabbix 日志记录器
zabbix_logger = logging.getLogger('bandwidth_logger')

def send_to_zabbix(metrics, zabbix_config, host_name):
    try:
        sender = ZabbixSender(zabbix_config['IP'], zabbix_config['PORT'])
        packets = []

        for metric in metrics:
            item_key = metric['key']
            item_value = metric['value']
            packet = ZabbixMetric(host_name, item_key, item_value)
            packets.append(packet)
            zabbix_logger.debug(f"Prepared packet: host_name={host_name}, item_key={item_key}, item_value={item_value}")

        result = sender.send(packets)

        if result.failed > 0:
            raise Exception(f"Failed to send some metrics: {result.failed}")

        zabbix_logger.info(f"Successfully sent data to Zabbix: {result.processed} processed, {result.failed} failed, {result.total} total")

    except Exception as e:
        zabbix_logger.error(f"Error sending data to Zabbix: {e}")

def query_bw_users_send_to_zabbix(brand_type):
    client = None
    try:
        client = get_livetv_influxdb_client()
        brands_config = load_config('brands.yaml')

        query_tool = InfluxDBQueryTool(client, brands_config)

        metrics = []
        for brand, info in brands_config['brands'][brand_type].items():
            try:
                bandwidth = query_tool.query_bandwidth(brand)
                users = query_tool.query_user(brand)
                metrics.append({'key': f'{brand}.bandwidth'.replace(' ', '_'), 'value': bandwidth})
                metrics.append({'key': f'{brand}.users'.replace(' ', '_'), 'value': users})
                zabbix_logger.info(f"{brand} Bandwidth: {bandwidth:.2f} Gbps, Users: {users}")
            except Exception as e:
                zabbix_logger.error(f"Error processing brand {brand}: {e}")

        send_to_zabbix(metrics, settings.ZABBIX_CONFIG['livetv_01'], "opt_live_info" if brand_type == 'opt' else "spc_live_info")
        send_to_zabbix(metrics, settings.ZABBIX_CONFIG['livetv_02'], "opt_live_info" if brand_type == 'opt' else "spc_live_info")
    except Exception as e:
        zabbix_logger.error(e)
    finally:
        if client:
            client.close()

def query_vod_bw_users_send_to_zabbix():
    client = None
    try:
        client = get_vod_influxdb_client()
        vod_query_tool = VodQueryTool(client)

        metrics = []

        # Query and log PM data
        try:
            pm_bandwidth = vod_query_tool.query_pm_bandwidth()
            pm_users = vod_query_tool.query_pm_users()
            pm_mobile_bandwidth = vod_query_tool.query_pm_mobile_bandwidth()
            pm_mobile_users = vod_query_tool.query_pm_mobile_users()
            metrics.append({'key': 'pm.bandwidth', 'value': pm_bandwidth})
            metrics.append({'key': 'pm.users', 'value': pm_users})
            metrics.append({'key': 'pm.mobile_bandwidth', 'value': pm_mobile_bandwidth})
            metrics.append({'key': 'pm.mobile_users', 'value': pm_mobile_users})
            zabbix_logger.info(
                f"PM Bandwidth: {pm_bandwidth:.2f} Gbps, PM Users: {pm_users}, PM Mobile Bandwidth: {pm_mobile_bandwidth:.2f} Gbps, PM Mobile Users: {pm_mobile_users}")
        except Exception as e:
            zabbix_logger.error(f"Error processing PM data: {e}")

        # Query and log MRT data
        try:
            mrt_bandwidth = vod_query_tool.query_mrt_bandwidth()
            mrt_users = vod_query_tool.query_mrt_users()
            mrt_mobile_bandwidth = vod_query_tool.query_mrt_mobile_bandwidth()
            mrt_mobile_users = vod_query_tool.query_mrt_mobile_users()
            metrics.append({'key': 'mrt.bandwidth', 'value': mrt_bandwidth})
            metrics.append({'key': 'mrt.users', 'value': mrt_users})
            metrics.append({'key': 'mrt.mobile_bandwidth', 'value': mrt_mobile_bandwidth})
            metrics.append({'key': 'mrt.mobile_users', 'value': mrt_mobile_users})
            zabbix_logger.info(
                f"MRT Bandwidth: {mrt_bandwidth:.2f} Gbps, MRT Users: {mrt_users}, MRT Mobile Bandwidth: {mrt_mobile_bandwidth:.2f} Gbps, MRT Mobile Users: {mrt_mobile_users}")
        except Exception as e:
            zabbix_logger.error(f"Error processing MRT data: {e}")

        send_to_zabbix(metrics, settings.ZABBIX_CONFIG['vod_01'], "MFC_Info")
        send_to_zabbix(metrics, settings.ZABBIX_CONFIG['vod_02'], "MFC_Info")
    except Exception as e:
        zabbix_logger.error(f"Error in query_and_log_vod: {e}")
    finally:
        if client:
            client.close()


