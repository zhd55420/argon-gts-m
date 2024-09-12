import yaml
import os


def load_config(file_name):
    file_path = os.path.join(os.path.dirname(__file__), '..', 'Configs', file_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

        # 调试信息：输出加载的配置文件内容
        print(f"Loaded config from {file_path}:")
        print(config)

        return config
