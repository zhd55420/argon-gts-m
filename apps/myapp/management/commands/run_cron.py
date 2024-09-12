from django.core.management.base import BaseCommand
from apps.myapp import cron  # 导入你需要执行的cron逻辑

class Command(BaseCommand):
    help = 'Runs the cron task.'

    def handle(self, *args, **kwargs):
        cron.run_resource_group_job()  # 执行cron逻辑，假设cron.py有一个run()函数
        self.stdout.write(self.style.SUCCESS('Successfully ran cron task.'))
