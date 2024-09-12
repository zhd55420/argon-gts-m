from django.db import models

# Create your models here.
class BrandData(models.Model):
    brand_name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50)  # 'mobile' or 'set-top box'
    user_count = models.IntegerField()
    bandwidth = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand_name} - {self.device_type}"