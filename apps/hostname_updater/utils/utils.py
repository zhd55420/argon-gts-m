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

def update_zabbix_hostname(ip_address, new_hostname, server_name):
    zapi = get_zabbix_connection(server_name)
    host_id = get_zabbix_host_id(ip_address, zapi)
    if host_id:
        zapi.host.update(
            hostid=host_id,
            host=new_hostname,
            name=new_hostname
        )
        return True
    return False

def get_zabbix_host_id(ip_address, zapi):
    result = zapi.host.get(filter={"ip": ip_address}, output=['hostid'])
    return result[0]['hostid'] if result else None

def update_telegraf_host(ip_address, new_hostname):
    telegraf_errors = []  # 存储 Telegraf 错误信息
    zabbix_errors = []    # 存储 Zabbix 错误信息

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 尝试连接到 SSH
        try:
            ssh.connect(ip_address, port=22, username=ssh_user['username'], password=ssh_user['password'], timeout=30)
            logger.info(f"Connected to {ip_address} on port 22")
        except Exception as e:
            logger.warning(f"Failed to connect to {ip_address} on port 22: {str(e)}. Trying port 28822...")
            ssh.connect(ip_address, port=28822, username=ssh_user['username'], password=ssh_user['password'], timeout=30)
            logger.info(f"Connected to {ip_address} on port 28822")

        # 修改 Telegraf 主机名并获取错误信息（如果有）
        telegraf_error = modify_telegraf_hostname(ssh, new_hostname)
        if telegraf_error:
            telegraf_errors.append(telegraf_error["message"])

        # 修改 Zabbix Agent 主机名并获取错误信息（如果有）
        zabbix_error = modify_zabbix_hostname(ssh, new_hostname)
        if zabbix_error:
            zabbix_errors.append(zabbix_error["message"])

        ssh.close()

        # 构造返回消息
        if telegraf_errors or zabbix_errors:
            message = "Some errors occurred during the update:\n"
            if telegraf_errors:
                message += "Telegraf Errors:\n" + "\n".join(telegraf_errors) + "\n"
            if zabbix_errors:
                message += "Zabbix Errors:\n" + "\n".join(zabbix_errors)
            logger.error(message)
            return {"success": False, "message": message}
        else:
            message = f"Successfully updated Telegraf and Zabbix Agent hostname for {ip_address} to {new_hostname}."
            logger.info(message)
            return {"success": True, "message": message}

    except paramiko.AuthenticationException:
        error_message = f"ssh Authentication failed when connecting to {ip_address}"
        logger.error(error_message)
        return {"success": False, "message": error_message}
    except paramiko.SSHException as sshException:
        error_message = f"Unable to establish SSH connection to {ip_address}: {str(sshException)}"
        logger.error(error_message)
        return {"success": False, "message": error_message}
    except paramiko.BadHostKeyException as badHostKeyException:
        error_message = f"Unable to verify server's host key for {ip_address}: {str(badHostKeyException)}"
        logger.error(error_message)
        return {"success": False, "message": error_message}
    except Exception as e:
        error_message = f"Failed to update hostnames for {ip_address}. Error: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"success": False, "message": error_message}


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

def update_telegraf_zabbix_config(ip_address, new_hostname, zabbix_server, zabbix_server_active, influxdb_urls, influxdb_username, influxdb_password, influxdb_database):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # 连接到目标主机 (默认端口 22)
            ssh.connect(ip_address, port=22, username=ssh_user['username'], password=ssh_user['password'], timeout=30)
            logger.info(f"Connected to {ip_address} on port 22")
        except Exception as e:
            # 如果默认端口 22 连接失败，尝试端口 28822
            logger.warning(f"Failed to connect to {ip_address} on port 22: {str(e)}. Trying port 28822...")
            ssh.connect(ip_address, port=28822, username=ssh_user['username'], password=ssh_user['password'], timeout=30)
            logger.info(f"Connected to {ip_address} on port 28822")

        # 修改 Zabbix Agent 配置文件
        update_zabbix_command = f'sed -i \'s/^Hostname=.*/Hostname={new_hostname}/\' /etc/zabbix/zabbix_agentd.conf'
        update_zabbix_command += f' && sed -i \'s/^Server=.*/Server={zabbix_server}/\' /etc/zabbix/zabbix_agentd.conf'
        update_zabbix_command += f' && sed -i \'s/^ServerActive=.*/ServerActive={zabbix_server_active}/\' /etc/zabbix/zabbix_agentd.conf'
        stdin, stdout, stderr = ssh.exec_command(update_zabbix_command)
        stderr_text = stderr.read().decode()
        if stderr_text:
            raise Exception(f"Error modifying Zabbix Agent config: {stderr_text}")

        # 添加 UserParameter 到 Zabbix 配置
        add_user_parameter = 'echo \'UserParameter=ifname, /bin/bash /etc/zabbix/discover_network_interfaces.sh\' | tee -a /etc/zabbix/zabbix_agentd.conf'
        stdin, stdout, stderr = ssh.exec_command(add_user_parameter)
        stderr_text = stderr.read().decode()
        if stderr_text:
            raise Exception(f"Error adding UserParameter to Zabbix Agent config: {stderr_text}")

        # 上传 discover_network_interfaces.sh 脚本到目标服务器
        sftp = ssh.open_sftp()
        local_script_path = '/home/gtsuser/remote_script/discover_network_interfaces.sh'  # 本地脚本的路径
        remote_script_path = '/etc/zabbix/discover_network_interfaces.sh'
        sftp.put(local_script_path, remote_script_path)
        logger.info(f"Uploaded discover_network_interfaces.sh to {ip_address}:{remote_script_path}")

        # 设置 discover_network_interfaces.sh 文件权限为可执行
        stdin, stdout, stderr = ssh.exec_command(f'chmod +x {remote_script_path}')
        stderr_text = stderr.read().decode()
        if stderr_text:
            raise Exception(f"Error setting executable permission on {remote_script_path}: {stderr_text}")

        # 修改 Telegraf 配置的 [[outputs.influxdb]] 部分
        update_telegraf_command = f'sed -i \'/[[outputs.influxdb]]/,/^$/{{s/urls = \\[.*\\]/urls = {influxdb_urls}/;s/username = .*/username = "{influxdb_username}"/;s/password = .*/password = "{influxdb_password}"/;s/database = .*/database = "{influxdb_database}"/}}\' /etc/telegraf/telegraf.conf'
        stdin, stdout, stderr = ssh.exec_command(update_telegraf_command)
        stderr_text = stderr.read().decode()
        if stderr_text:
            raise Exception(f"Error modifying Telegraf config: {stderr_text}")

        # 重启 Zabbix Agent 和 Telegraf 服务
        ssh.exec_command('systemctl restart zabbix-agent')
        ssh.exec_command('systemctl restart telegraf')

        ssh.close()
        message = f"Successfully updated Zabbix and Telegraf configuration for {ip_address}."
        logger.info(message)
        return {"success": True, "message": message}

    except paramiko.AuthenticationException:
        return {"success": False, "message": f"SSH Authentication failed for {ip_address}"}
    except Exception as e:
        logger.error(f"Error updating Zabbix and Telegraf configuration for {ip_address}: {e}")
        return {"success": False, "message": str(e)}