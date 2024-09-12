import datetime

from django.shortcuts import render
from .Models.brands import BrandData
from django.http import JsonResponse
from django.db.models import Sum
from apps.myapp.Utils.convert_cfg import load_config
# Create your views here.
from django.http import HttpResponse

from django.http import JsonResponse
from apps.myapp.Utils.convert_cfg import load_config
from apps.myapp.Utils.get_brand_users_bw import InfluxDBQueryTool
from apps.myapp.Utils.send_to_lark import send_message_to_optlark
from influxdb import InfluxDBClient

from .Utils.get_influxdb_client import get_livetv_influxdb_client
from .Utils.get_tracker_user import TrackerInfluxDBQueryTool


def get_brand_data(request):
    data = BrandData.objects.values('brand_name', 'device_type').annotate(
        total_users=Sum('user_count'),
        total_bandwidth=Sum('bandwidth')
    )
    return JsonResponse(list(data), safe=False)


def show_release_id(request, brand_name):
    brands_config = load_config('brands.yaml')
    release_id = brands_config['brands'].get(brand_name, {}).get('release_id', '未知品牌')
    return HttpResponse(f"品牌{brand_name}的release_id是{release_id}")
def show_databases_url(request, company_name):
    db_config = load_config('databases.yaml')
    url = db_config['databases'].get(company_name, {}).get('url', '未知品牌')
    return HttpResponse(f"influxdb{company_name}的url是{url}")


def display_brand_data(request):
    client = None
    try:
        client = get_livetv_influxdb_client()
        brands_config = load_config('brands.yaml')  # 应指向YAML文件的正确路径
        tracker_query_tool = TrackerInfluxDBQueryTool(client, brands_config)
        query_tool = InfluxDBQueryTool(client, brands_config)

        datetime_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"SZ TIME: {datetime_now}\n"

        content = []

        for brand, info in brands_config['brands'].items():
            bandwidth = query_tool.query_bandwidth(brand)
            users = query_tool.query_user(brand)
            content.append(f"{brand} Bandwidth: {bandwidth:.2f} Gbps")
            content.append(f"{brand} Users: {users}")

        for tracker, info in brands_config['Trackers'].items():
            users = tracker_query_tool.query_user(tracker)
            content.append(f"{tracker} Tracker Users: {users}")

        response_body = "\n".join([subject] + content)
        send_message_to_optlark(response_body)
        return HttpResponse(response_body, content_type="text/plain")
    except Exception as e:
        return HttpResponse(f"An error occurred: {str(e)}", status=500)
    finally:
        if client:
            client.close()

