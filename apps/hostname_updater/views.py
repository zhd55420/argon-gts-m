import os
from logging.handlers import TimedRotatingFileHandler
import yaml
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse,HttpResponseRedirect
import logging
from .forms import HostnameUpdateForm,ResourceGroupForm, PRTForm, TrackerForm,ZabbixDeleteForm
from .utils.utils import update_zabbix_hostname, update_telegraf_host, get_zabbix_connection, get_zabbix_host_id, \
    update_telegraf_zabbix_config
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# 配置 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

logger = logging.getLogger('hostname_updater')
@login_required(login_url="/login/")
def update_hostname(request):
    success_messages = []
    error_messages = []
    zabbix_servers = [(key, f"{key.replace('_', ' ').title()} Server") for key in settings.ZABBIX_CONFIG.keys()]

    if request.method == 'POST':
        form = HostnameUpdateForm(request.POST)
        form.fields['zabbix_server'].choices = zabbix_servers
        if form.is_valid():
            single_ip_address = form.cleaned_data['single_ip_address']
            single_new_hostname = form.cleaned_data['single_new_hostname']
            bulk_input = form.cleaned_data['bulk_input']
            zabbix_server = form.cleaned_data['zabbix_server']

            # 处理单个IP和主机名更新
            if single_ip_address and single_new_hostname:
                result = update_zabbix_hostname(single_ip_address, single_new_hostname, zabbix_server)
                if result:
                    update_telegraf_host(single_ip_address, single_new_hostname)
                    message = f"Successfully updated hostname for {single_ip_address} to {single_new_hostname}."
                    success_messages.append(message)
                    logger.info(message)
                else:
                    message = f"Failed to update hostname for {single_ip_address}."
                    error_messages.append(message)
                    logger.error(message)

            # 处理批量IP和主机名更新
            if bulk_input:
                bulk_lines = bulk_input.splitlines()
                for line in bulk_lines:
                    try:
                        ip_address, new_hostname = map(str.strip, line.split(','))
                        result = update_zabbix_hostname(ip_address, new_hostname, zabbix_server)
                        if result:
                            telegraf_result = update_telegraf_host(ip_address, new_hostname)
                            message = f"Successfully updated hostname for {ip_address} to {new_hostname}."
                            success_messages.append(message)
                            success_messages.append(telegraf_result['message']) if telegraf_result[
                                'success'] else error_messages.append(telegraf_result['message'])
                            logger.info(message)
                        else:
                            message = f"Failed to update hostname for {ip_address}."
                            error_messages.append(message)
                            logger.error(message)
                    except Exception as e:
                        message = f"Error processing line '{line}': {str(e)}"
                        error_messages.append(message)
                        logger.error(message)

    else:
        form = HostnameUpdateForm()
        form.fields['zabbix_server'].choices = zabbix_servers

    context = {
        'form': form,
        'success_messages': success_messages,
        'error_messages': error_messages,
        'zabbix_servers': zabbix_servers,
    }

    return render(request, 'hostname_updater/update_hostname.html', context)


# 获取项目根目录
BASE_DIR = settings.BASE_DIR

# 拼接出 resource_groups.yaml 的路径
RESOURCE_GROUPS_YAML_PATH = os.path.join(BASE_DIR, 'apps/myapp', 'Configs', 'resource_groups.yaml')
def load_resource_groups():
    with open(RESOURCE_GROUPS_YAML_PATH, 'r') as file:
        data = yaml.safe_load(file)
        return data.get('resource_groups', {})

def save_resource_groups(data):
    with open(RESOURCE_GROUPS_YAML_PATH, 'w') as file:
        yaml.safe_dump({'resource_groups': data}, file)



@login_required(login_url="/login/")
def manage_resources(request):
    messages = []
    resource_groups = load_resource_groups()
    selected_group = None
    prts = []
    trackers = []

    if request.method == 'POST':
        if 'select_group' in request.POST:
            selected_group = request.POST.get('group_name')
            if selected_group:
                prts = resource_groups[selected_group]['prt']
                trackers = resource_groups[selected_group]['trackers']

        elif 'submit_group' in request.POST:
            group_form = ResourceGroupForm(request.POST)
            if group_form.is_valid():
                action = group_form.cleaned_data['action']
                group_name = group_form.cleaned_data['group_name']
                if action == 'add':
                    if group_name in resource_groups:
                        messages.append(f"⚠️ Resource group '{group_name}' already exists.")
                    else:
                        resource_groups[group_name] = {'prt': [], 'tracker': []}
                        messages.append(f"✅ Resource group '{group_name}' added.")
                elif action == 'delete':
                    if group_name in resource_groups:
                        del resource_groups[group_name]
                        messages.append(f"❌ Resource group '{group_name}' deleted.")
                    else:
                        messages.append(f"⚠️ Resource group '{group_name}' does not exist.")
                save_resource_groups(resource_groups)

        elif 'submit_prt' in request.POST:
            prt_form = PRTForm(request.POST)
            if prt_form.is_valid():
                action = prt_form.cleaned_data['action']
                group_name = prt_form.cleaned_data['group_name']
                prt_values = prt_form.cleaned_data['prt_value'].splitlines()  # 支持批量输入，按行分割
                for prt_value in prt_values:
                    prt_value = prt_value.strip()
                    if action == 'add':
                        if prt_value in resource_groups[group_name]['prt']:
                            messages.append(f"⚠️ PRT '{prt_value}' already exists in '{group_name}'.")
                        else:
                            resource_groups[group_name]['prt'].append(prt_value)
                            messages.append(f"✅ PRT '{prt_value}' added to '{group_name}'.")
                    elif action == 'delete':
                        if prt_value in resource_groups[group_name]['prt']:
                            resource_groups[group_name]['prt'].remove(prt_value)
                            messages.append(f"❌ PRT '{prt_value}' deleted from '{group_name}'.")
                        else:
                            messages.append(f"⚠️ PRT '{prt_value}' does not exist in '{group_name}'.")
                save_resource_groups(resource_groups)
            else:
                print(prt_form.errors)

        elif 'submit_tracker' in request.POST:
            tracker_form = TrackerForm(request.POST)
            if tracker_form.is_valid():
                action = tracker_form.cleaned_data['action']
                group_name = tracker_form.cleaned_data['group_name']
                tracker_values = tracker_form.cleaned_data['tracker_value'].splitlines()  # 支持批量输入，按行分割
                for tracker_value in tracker_values:
                    tracker_value = tracker_value.strip()
                    if action == 'add':
                        if tracker_value in resource_groups[group_name]['trackers']:
                            messages.append(f"⚠️ Tracker '{tracker_value}' already exists in '{group_name}'.")
                        else:
                            resource_groups[group_name]['trackers'].append(tracker_value)
                            messages.append(f"✅ Tracker '{tracker_value}' added to '{group_name}'.")
                    elif action == 'delete':
                        if tracker_value in resource_groups[group_name]['trackers']:
                            resource_groups[group_name]['trackers'].remove(tracker_value)
                            messages.append(f"❌ Tracker '{tracker_value}' deleted from '{group_name}'.")
                        else:
                            messages.append(f"⚠️ Tracker '{tracker_value}' does not exist in '{group_name}'.")
                save_resource_groups(resource_groups)

    # 初始化表单并设置默认选项
    group_form = ResourceGroupForm()
    prt_form = PRTForm(initial={'group_name': selected_group})
    tracker_form = TrackerForm(initial={'group_name': selected_group})

    context = {
        'group_form': group_form,
        'prt_form': prt_form,
        'tracker_form': tracker_form,
        'messages': messages,
        'resource_groups': resource_groups,
        'selected_group': selected_group,
        'prts': prts,
        'trackers': trackers,
    }
    return render(request, 'hostname_updater/manage_resources.html', context)


@login_required(login_url="/login/")
def zabbix_delete(request):
    success_messages = []
    error_messages = []
    zabbix_servers = [(key, f"{key.replace('_', ' ').title()} Server") for key in settings.ZABBIX_CONFIG.keys()]

    if request.method == 'POST':
        form = ZabbixDeleteForm(request.POST)
        form.fields['zabbix_server'].choices = zabbix_servers

        if form.is_valid():
            server_name = form.cleaned_data['zabbix_server']
            ip_addresses = form.cleaned_data['ip_addresses'].splitlines()

            for ip_address in ip_addresses:
                ip_address = ip_address.strip()
                if not ip_address:
                    continue

                try:
                    zapi = get_zabbix_connection(server_name)
                    host_id = get_zabbix_host_id(ip_address,zapi)

                    if host_id:
                        zapi.host.delete(host_id)  # 确保传递的 `host_id` 是一个列表
                        message = f"Successfully deleted monitoring for IP: {ip_address} on {server_name}"
                        messages.success(request, message)
                        success_messages.append(message)
                    else:
                        message = f"No monitoring found for IP: {ip_address} on {server_name}"
                        messages.warning(request, message)
                        error_messages.append(message)

                except Exception as e:
                    message = f"Failed to delete monitoring for IP: {ip_address} on {server_name}. Error: {str(e)}"
                    messages.error(request, message)
                    error_messages.append(message)


    else:
        form = ZabbixDeleteForm()
        form.fields['zabbix_server'].choices = zabbix_servers

    context = {
        'form': form,
        'success_messages': success_messages,
        'error_messages': error_messages,
        'zabbix_servers': zabbix_servers,
    }

    return render(request, 'hostname_updater/zabbix_delete.html', context)

@login_required(login_url="/login/")
def select_zabbix_telegraf_config(request):
    if request.method == 'POST':
        # 获取表单数据
        bulk_input = request.POST.get('bulk_input')
        zabbix_config = request.POST.get('zabbix_config')
        influxdb_database = request.POST.get('influxdb_database')

        # 获取用户选择的 Zabbix 和 Telegraf 配置
        zabbix_telegraf_config = settings.ZABBIX_TELEGRAF_CONFIG.get(zabbix_config)

        if zabbix_telegraf_config:
            zabbix_server = zabbix_telegraf_config['zabbix_server']
            zabbix_server_active = zabbix_telegraf_config['zabbix_server_active']
            influxdb_urls = zabbix_telegraf_config['influxdb_urls']
            influxdb_username = zabbix_telegraf_config['influxdb_username']
            influxdb_password = zabbix_telegraf_config['influxdb_password']

            # 处理成功和错误消息列表
            success_messages = []
            error_messages = []

            # 解析批量输入的 IP 地址和主机名
            lines = bulk_input.strip().split('\n')
            for line in lines:
                try:
                    ip_address, new_hostname = line.split(',')
                    ip_address = ip_address.strip()
                    new_hostname = new_hostname.strip()

                    # 调用更新方法进行每个 IP 的配置更新
                    result = update_telegraf_zabbix_config(
                        ip_address,
                        new_hostname,
                        zabbix_server,
                        zabbix_server_active,
                        influxdb_urls,
                        influxdb_username,
                        influxdb_password,
                        influxdb_database
                    )

                    # 根据结果添加成功或错误消息
                    if result['success']:
                        success_messages.append(f"{ip_address}: {result['message']}")
                    else:
                        error_messages.append(f"{ip_address}: {result['message']}")
                except ValueError:
                    error_messages.append(f"Invalid format for line: {line}")

            # 渲染模板并显示结果
            return render(request, 'hostname_updater/select_zabbix_telegraf_config.html', {
                'success_messages': success_messages,
                'error_messages': error_messages,
            })
        else:
            error_messages = ["Invalid Zabbix or Telegraf configuration selection."]
            return render(request, 'hostname_updater/select_zabbix_telegraf_config.html', {
                'error_messages': error_messages,
            })

    # GET 请求时渲染选择页面
    return render(request, 'hostname_updater/select_zabbix_telegraf_config.html')


# 加载和保存 YAML 文件的方法
BRANDS_YAML_PATH = os.path.join(settings.BASE_DIR, 'apps', 'myapp', 'Configs', 'brands.yaml')

def load_brands_config():
    try:
        with open(BRANDS_YAML_PATH, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {'brands': {}, 'trackers': {}}

def save_brands_config(config_data):
    with open(BRANDS_YAML_PATH, 'w') as file:
        yaml.safe_dump(config_data, file)

def manage_brands_trackers(request):
    messages = []
    selected_business_unit = None

    # 加载 Brands 和 Trackers 配置
    config = load_brands_config()
    brands = config.get('brands', {})
    trackers = config.get('trackers', {})

    # 获取所有的 Business Units (公司名称，如 opt, spc)
    business_units = brands.keys()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')  # 获取表单类型

        # 处理 Business Unit 选择
        if form_type == 'select_business_unit':
            selected_business_unit = request.POST.get('business_unit')
            if selected_business_unit:
                # 加载选定 Business Unit 下的品牌
                brands = brands.get(selected_business_unit, {})

        # 处理 Brands 表单
        elif form_type == 'submit_brand':
            business_unit = request.POST.get('business_unit')  # 获取公司信息
            brand_name = request.POST.get('brand_name')
            release_id = request.POST.get('release_id')
            action = request.POST.get('brand_action')

            if business_unit and brand_name and release_id:
                if action == 'add':
                    if business_unit not in brands:
                        brands[business_unit] = {}

                    if brand_name in brands[business_unit]:
                        messages.append(f"⚠️ Brand '{brand_name}' already exists in '{business_unit}'.")
                    else:
                        brands[business_unit][brand_name] = {'release_id': release_id}
                        messages.append(f"✅ Brand '{brand_name}' added to '{business_unit}'.")
                elif action == 'delete':
                    if business_unit in brands and brand_name in brands[business_unit]:
                        del brands[business_unit][brand_name]
                        messages.append(f"❌ Brand '{brand_name}' deleted from '{business_unit}'.")
                    else:
                        messages.append(f"⚠️ Brand '{brand_name}' does not exist in '{business_unit}'.")

                # 保存更新后的 Brands
                config['brands'] = brands
                save_brands_config(config)

        # 处理 Trackers 表单
        elif form_type == 'submit_tracker':
            business_unit = request.POST.get('business_unit')  # 获取公司信息
            tracker_name = request.POST.get('tracker_name')
            server_code = request.POST.get('server_code')
            action = request.POST.get('tracker_action')

            if tracker_name and server_code:
                if action == 'add':
                    if tracker_name in trackers:
                        messages.append(f"⚠️ Tracker '{tracker_name}' already exists.")
                    else:
                        trackers[tracker_name] = {'server_code': server_code}
                        messages.append(f"✅ Tracker '{tracker_name}' added with server code '{server_code}'.")
                elif action == 'delete':
                    if tracker_name in trackers:
                        del trackers[tracker_name]
                        messages.append(f"❌ Tracker '{tracker_name}' deleted.")
                    else:
                        messages.append(f"⚠️ Tracker '{tracker_name}' does not exist.")

                # 保存更新后的 Trackers
                config['trackers'] = trackers
                save_brands_config(config)

    context = {
        'brands': brands,
        'trackers': trackers,
        'business_units': business_units,
        'messages': messages,
        'selected_business_unit': selected_business_unit,
    }

    return render(request, 'hostname_updater/manage_brands_trackers.html', context)