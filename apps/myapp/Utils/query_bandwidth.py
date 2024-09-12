import datetime
import logging
import pytz
from apps.myapp.Utils.get_influxdb_client import get_livetv_influxdb_client,get_vod_influxdb_client
from apps.myapp.Utils.get_brand_users_bw import InfluxDBQueryTool
from apps.myapp.Utils.convert_cfg import load_config
from apps.myapp.Utils.get_tracker_user import TrackerInfluxDBQueryTool
from apps.myapp.Utils.get_resource_group_users_bw import ResourceGroupQueryTool
from apps.myapp.Utils.get_resource_group_tracker_user import ResourceTrackerQueryTool
from apps.myapp.Utils.get_vod_trackers_user import VodTrackerQueryTool
from apps.myapp.Utils.get_vod_users_bw import VodQueryTool

logger = logging.getLogger('bandwidth_logger')


def query_and_log_bandwidth(brand_type, send_message_func):
    client = None
    try:
        client = get_livetv_influxdb_client()
        brands_config = load_config('brands.yaml')  # 应指向YAML文件的正确路径

        query_tool = InfluxDBQueryTool(client, brands_config)

        china_tz = pytz.timezone('Asia/Shanghai')
        datetime_now = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")
        subject = f"SZ TIME: {datetime_now}\n"

        content = []
        for brand, info in brands_config['brands'][brand_type].items():
            try:
                bandwidth = query_tool.query_bandwidth(brand)
                users = query_tool.query_user(brand)
                content.append(f"{brand} Bandwidth: {bandwidth:.2f} Gbps")
                content.append(f"{brand} Users: {users}")
                logger.info(f"{brand} Bandwidth: {bandwidth:.2f} Gbps, Users: {users}")
            except Exception as e:
                logger.error(f"Error processing brand {brand}: {e}")

        response_body = "\n".join([subject] + content)

        # 发送到 Lark
        send_message_func(response_body)
    except Exception as e:
        logger.error(e)
    finally:
        if client:
            client.close()

def query_and_log_tracker_users(tracker_type, send_message_func):
    client = None
    try:
        client = get_livetv_influxdb_client()
        tracker_config = load_config('brands.yaml')

        query_tool = TrackerInfluxDBQueryTool(client, tracker_config)

        china_tz = pytz.timezone('Asia/Shanghai')
        datetime_now = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")
        subject = f"SZ TIME: {datetime_now}\n"

        content = []
        for tracker in tracker_config['Trackers']:
            try:
                users = query_tool.query_user(tracker)
                content.append(f"{tracker} Tracker Users: {users}")
                logger.info(f"{tracker} Tracker Users: {users}")
            except Exception as e:
                logger.error(f"Error processing tracker {tracker}: {e}")

        response_body = "\n".join([subject] + content)
        send_message_func(response_body)
    except Exception as e:
        logger.error(e)
    finally:
        if client:
            client.close()



def query_and_log_resource_groups(send_message_func):
    client = None
    try:
        client = get_livetv_influxdb_client()
        resource_group_config = load_config('resource_groups.yaml')

        resource_group_query_tool = ResourceGroupQueryTool(client)
        tracker_query_tool = ResourceTrackerQueryTool(client)

        china_tz = pytz.timezone('Asia/Shanghai')
        datetime_now = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")
        subject = f"SZ TIME: {datetime_now}\n"

        content = []
        for group, servers in resource_group_config['resource_groups'].items():
            try:
                prt_bandwidth = resource_group_query_tool.query_prt_bandwidth(servers['prt'])
                prt_users = resource_group_query_tool.query_prt_users(servers['prt'])
                tracker_users = tracker_query_tool.query_tracker_users(servers['trackers'])
                content.append(f"{group} PRT Bandwidth: {prt_bandwidth:.2f} Gbps")
                content.append(f"{group} PRT Users: {prt_users}")
                content.append(f"{group} Tracker Users: {tracker_users}")
                logger.info(f"{group} PRT Bandwidth: {prt_bandwidth:.2f} Gbps, PRT Users: {prt_users}, Tracker Users: {tracker_users}")
            except Exception as e:
                logger.error(f"Error processing group {group}: {e}")

        full_message = subject + "\n".join(content)
        send_message_func(full_message)
    except Exception as e:
        logger.error(f"Error in query_and_log_resource_group: {e}")
    finally:
        if client:
            client.close()

def query_and_log_vod(send_message_func):
    client = None
    try:
        client = get_vod_influxdb_client()
        vod_query_tool = VodQueryTool(client)
        vod_tracker_query_tool = VodTrackerQueryTool(client)

        china_tz = pytz.timezone('Asia/Shanghai')
        datetime_now = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")
        subject = f"SZ TIME: {datetime_now}\n"

        content = []

        # Query and log PM data
        try:
            pm_bandwidth = vod_query_tool.query_pm_bandwidth()
            pm_users = vod_query_tool.query_pm_users()
            pm_mobile_bandwidth = vod_query_tool.query_pm_mobile_bandwidth()
            pm_mobile_users = vod_query_tool.query_pm_mobile_users()
            vod_tracker_users = vod_tracker_query_tool.query_tracker_users()
            content.append(f"PM Bandwidth: {pm_bandwidth:.2f} Gbps")
            content.append(f"PM Users: {pm_users}")
            content.append(f"PM Mobile Bandwidth: {pm_mobile_bandwidth:.2f} Gbps")
            content.append(f"PM Mobile Users: {pm_mobile_users}")
            content.append(f"VOD tracker Users: {vod_tracker_users}")
            logger.info(f"PM Bandwidth: {pm_bandwidth:.2f} Gbps, PM Users: {pm_users}, PM Mobile Bandwidth: {pm_mobile_bandwidth:.2f} Gbps,PM Mobile Users: {pm_mobile_users} ,VOD tracker Users: {vod_tracker_users}  ")
        except Exception as e:
            logger.error(f"Error processing PM data: {e}")

        # Query and log MRT data
        try:
            mrt_bandwidth = vod_query_tool.query_mrt_bandwidth()
            mrt_users = vod_query_tool.query_mrt_users()
            mrt_mobile_bandwidth = vod_query_tool.query_mrt_mobile_bandwidth()
            mrt_mobile_users = vod_query_tool.query_mrt_mobile_users()
            content.append(f"MRT Bandwidth: {mrt_bandwidth:.2f} Gbps")
            content.append(f"MRT Users: {mrt_users}")
            content.append(f"MRT Mobile Bandwidth: {mrt_mobile_bandwidth:.2f} Gbps")
            content.append(f"MRT Mobile Users: {mrt_mobile_users}")
            logger.info(f"MRT Bandwidth: {mrt_bandwidth:.2f} Gbps, MRT Users: {mrt_users},MRT Mobile Bandwidth: {mrt_mobile_bandwidth:.2f} Gbps,MRT Mobile Users: {mrt_mobile_users}  ")
        except Exception as e:
            logger.error(f"Error processing MRT data: {e}")

        full_message = subject + "\n".join(content)
        send_message_func(full_message)
    except Exception as e:
        logger.error(f"Error in query_and_log_vod: {e}")
    finally:
        if client:
            client.close()








