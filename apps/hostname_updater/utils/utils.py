# utils.py
from pyzabbix import ZabbixAPI
from django.conf import settings
import paramiko
import logging
from core.settings import ssh_user

logger = logging.getLogger('hostname_updater')

def get_zabbix_connection(server_name):
    server_config = settings.ZABBIX_CONFIG.get(server_name)
    if not server_config:
        raise ValueError(f"Unknown Zabbix server: {server_name}")

    zapi = ZabbixAPI(url=server_config['API_URL'],user=server_config['API_USER'],password=server_config['API_PASSWORD'])
    return zapi

def update_zabbix_web_hostname(ip_address, new_hostname, server_name):
    zapi = get_zabbix_connection(server_name)
    host_id = get_zabbix_host_id(ip_address, zapi)
    if host_id:
        zapi.host.update(
            hostid=host_id,
            host=new_hostname,
            name=new_hostname
        )
        return {"success": True, "message": f"Successfully updated all services for {ip_address} to {new_hostname}."}
    return False

def get_zabbix_host_id(ip_address, zapi):
    result = zapi.host.get(filter={"ip": ip_address}, output=['hostid'])
    return result[0]['hostid'] if result else None

def connect_with_multiple_ports(ssh, ip_address, username, password, ports=(22, 28822), timeout=30):
    for port in ports:
        try:
            ssh.connect(ip_address, port=port, username=ssh_user['username'], password=ssh_user['password'], timeout=timeout)
            logger.info(f"Connected to {ip_address} on port {port}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to {ip_address} on port {port}: {str(e)}")
    logger.error(f"Failed to connect to {ip_address} on all ports: {ports}")
    return False


def update_server_config_host(ip_address, new_hostname):
    errors = {"telegraf": [], "zabbix_agent": []}

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if not connect_with_multiple_ports(ssh, ip_address, ssh_user['username'], ssh_user['password']):
            return {"success": False, "message": f"Failed to connect to {ip_address} on all ports"}

        # 更新各服务配置
        update_tasks = [
            ("telegraf", modify_telegraf_hostname),
            ("zabbix_agent", modify_zabbix_hostname),
        ]

        for service, task in update_tasks:
            error = task(ssh, new_hostname)
            if error:
                errors[service].append(error["message"])

        # 返回结果
        if any(errors.values()):
            return {
                "success": False,
                "telegraf": {"success": not errors["telegraf"], "message": "\n".join(errors["telegraf"])},
                "zabbix_agent": {"success": not errors["zabbix_agent"], "message": "\n".join(errors["zabbix_agent"])},
            }
        else:
            return {"success": True, "message": f"Successfully updated all services for {ip_address} to {new_hostname}."}

    except Exception as e:
        logger.error(f"Unexpected error for {ip_address}: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Unexpected error: {str(e)}"}
    finally:
        ssh.close()



def modify_telegraf_hostname(ssh, new_hostname):
    # 检查 Telegraf 配置文件是否存在
    check_command = 'test -f /etc/telegraf/telegraf.conf'
    stdin, stdout, stderr = ssh.exec_command(check_command)
    if stderr.read().decode():
        return {"success": False, "message": "Telegraf config file does not exist: /etc/telegraf/telegraf.conf"}

    update_telegraf_command = f'sudo sed -i \'s/^  hostname = .*/  hostname = "{new_hostname}"/\' /etc/telegraf/telegraf.conf'
    stdin, stdout, stderr = ssh.exec_command(update_telegraf_command)
    stderr_text = stderr.read().decode()
    if stderr_text:
        return {"success": False, "message": f"Error modifying Telegraf config: {stderr_text}"}

    # 重启 Telegraf 服务
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart telegraf')
    stderr_text = stderr.read().decode()
    if stderr_text:
        return {"success": False, "message": f"Error restarting Telegraf: {stderr_text}"}

    logger.info("Telegraf hostname updated successfully.")
    return None  # 返回 None 表示成功


def modify_zabbix_hostname(ssh, new_hostname):
    update_zabbix_command = f'sudo sed -i \'s/^Hostname=.*/Hostname={new_hostname}/\' /etc/zabbix/zabbix_agentd.conf'
    stdin, stdout, stderr = ssh.exec_command(update_zabbix_command)
    stderr_text = stderr.read().decode()
    if stderr_text:
        return {"success": False, "message": f"Error modifying Zabbix Agent config: {stderr_text}"}

    # 重启 Zabbix Agent 服务
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart zabbix-agent')
    stderr_text = stderr.read().decode()
    if stderr_text:
        return {"success": False, "message": f"Error restarting Zabbix Agent: {stderr_text}"}

    logger.info("Zabbix Agent hostname updated successfully.")
    return None  # 返回 None 表示成功

def process_hostname_update(ip_address, new_hostname, zabbix_server, user_info, success_messages, error_messages):
    """
    封装主机名更新逻辑，更新 Zabbix 和服务器配置，并将成功或失败消息分别记录到 success_messages 和 error_messages。
    """
    try:
        # 更新 Zabbix 中的主机名
        zabbix_result = update_zabbix_web_hostname(ip_address, new_hostname, zabbix_server)

        # 记录 Zabbix 更新的结果
        if zabbix_result:
            zabbix_success_message = f"Successfully updated hostname for {ip_address} in Zabbix."
            success_messages.append(zabbix_success_message)
            logger.info(f"{user_info} : {zabbix_success_message}")
        else:
            zabbix_error_message = f"Failed to update hostname for {ip_address}. Not found in Zabbix."
            error_messages.append(zabbix_error_message)
            logger.error(f"{user_info} : {zabbix_error_message}")

        # 更新服务器配置（Telegraf 和 Zabbix Agent）
        server_result = update_server_config_host(ip_address, new_hostname)

        # 记录服务器配置更新的结果
        if server_result['success']:
            server_success_message = server_result['message']
            success_messages.append(server_success_message)
            logger.info(f"{user_info} : {server_success_message}")
        else:
            server_error_message = server_result['message']
            error_messages.append(server_error_message)
            logger.error(f"{user_info} : {server_error_message}")

        # 返回合并后的结果（既有成功，也可能有失败）
        return {
            "success": not error_messages,  # 如果 error_messages 为空则返回 True，否则 False
            "message": '\n'.join(success_messages + error_messages)
        }

    except Exception as e:
        # 捕获任何异常并记录错误
        error_message = f"Error updating hostname for {ip_address}: {str(e)}"
        error_messages.append(error_message)
        logger.error(f"{user_info} : {error_message}", exc_info=True)

        return {"success": False, "message": error_message}



def update_zabbix_config(ssh, new_hostname, zabbix_server, zabbix_server_active):
    try:
        # 更新 Zabbix Agent 配置
        zabbix_update_command = (
            f"sudo sed -i 's/^Hostname=.*/Hostname={new_hostname}/' /etc/zabbix/zabbix_agentd.conf && "
            f"sudo sed -i 's/^Server=.*/Server={zabbix_server}/' /etc/zabbix/zabbix_agentd.conf && "
            f"sudo sed -i 's/^ServerActive=.*/ServerActive={zabbix_server_active}/' /etc/zabbix/zabbix_agentd.conf"
        )
        stdin, stdout, stderr = ssh.exec_command(zabbix_update_command)
        stderr_text = stderr.read().decode()
        if stderr_text:
            raise Exception(f"Error modifying Zabbix config: {stderr_text}")

        # 重启 Zabbix Agent
        ssh.exec_command('sudo systemctl restart zabbix-agent')

        return {"success": True, "message": "Zabbix configuration updated successfully."}

    except Exception as e:
        logger.error(f"Error updating Zabbix configuration: {e}")
        return {"success": False, "message": str(e)}


def escape_ampersand(input_string):
    """Escape only the '&' character for sed."""
    return input_string.replace('&', '\\&')

def update_telegraf_config(ssh, influxdb_urls, influxdb_username, influxdb_password, influxdb_database):
    try:
        # 只对&字符转义
        escaped_password = escape_ampersand(influxdb_password)

        # 确保 URLs 是字符串，格式为 '["http://example.com"]'
        escaped_urls = escape_ampersand(influxdb_urls)

        # 更新 Telegraf 配置
        telegraf_command = f"""sudo sed -i -e 's|^\\(\\s*password = "\\).*|\\1{escaped_password}\\"|' \
-e 's|^\\(\\s*username = \\).*|  username = "{influxdb_username}"|' \
-e 's|^\\(\\s*database = \\).*|  database = "{influxdb_database}"|' \
-e 's|^\\(\\s*urls = \\).*|  urls = {escaped_urls}|' \
/etc/telegraf/telegraf.conf
"""
        # 执行命令来更新配置
        stdin, stdout, stderr = ssh.exec_command(telegraf_command)
        stderr_text = stderr.read().decode()
        if stderr_text:
            raise Exception(f"Error modifying Telegraf config: {stderr_text}")

        # 重启 Telegraf
        ssh.exec_command('sudo systemctl restart telegraf')

        return {"success": True, "message": "Telegraf configuration updated successfully."}

    except Exception as e:
        logger.error(f"Error updating Telegraf configuration: {e}")
        return {"success": False, "message": str(e)}


def update_telegraf_zabbix_config(ip_address, new_hostname, zabbix_server, zabbix_server_active, influxdb_urls,
                                  influxdb_username, influxdb_password, influxdb_database):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 连接到目标主机 (最大的可能性)
        try:
            ssh.connect(ip_address, port=22, username=ssh_user['username'], password=ssh_user['password'], timeout=30)
            logger.info(f"Connected to {ip_address} on port 22")
        except Exception as e:
            logger.warning(f"Failed to connect to {ip_address} on port 22: {str(e)}. Trying port 28822...")
            ssh.connect(ip_address, port=28822, username=ssh_user['username'], password=ssh_user['password'],
                        timeout=30)
            logger.info(f"Connected to {ip_address} on port 28822")

        # 更新 Zabbix 配置
        zabbix_result = update_zabbix_config(ssh, new_hostname, zabbix_server, zabbix_server_active)

        # 更新 Telegraf 配置
        telegraf_result = update_telegraf_config(ssh, influxdb_urls, influxdb_username, influxdb_password,
                                                 influxdb_database)

        # 返回综合结果
        return {
            "success": zabbix_result['success'] and telegraf_result['success'],
            "messages": [zabbix_result['message'], telegraf_result['message']]
        }

    except paramiko.AuthenticationException:
        return {"success": False, "message": f"SSH Authentication failed for {ip_address}"}
    except Exception as e:
        logger.error(f"Error updating Zabbix and Telegraf configuration for {ip_address}: {e}")
        return {"success": False, "message": str(e)}
    finally:
        ssh.close()



