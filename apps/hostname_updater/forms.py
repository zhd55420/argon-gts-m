from django import forms

class HostnameUpdateForm(forms.Form):
    bulk_input = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', })
    )
    zabbix_server = forms.ChoiceField(
        choices=[],  # 这里不需要默认值，动态生成
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class ResourceGroupForm(forms.Form):
    action = forms.ChoiceField(choices=[('add', 'Add'), ('delete', 'Delete')], label='Action')
    group_name = forms.CharField(label='Resource Group Name')

    def clean(self):
        cleaned_data = super().clean()

        # 去除空值
        for key, value in cleaned_data.items():
            if value == '':
                cleaned_data[key] = None  # 如果不希望空值进入数据库
            else:
                # 移除输入中的空格
                cleaned_data[key] = value.strip()

        return cleaned_data

class PRTForm(forms.Form):
    action = forms.ChoiceField(choices=[('add', 'Add'), ('delete', 'Delete')], label='Action', required=True)
    group_name = forms.CharField(label='Resource Group Name', required=True,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))  # 设置为只读
    prt_value = forms.CharField(label='PRT Server ID', required=True,widget=forms.Textarea(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()

        # 去除空值
        for key, value in cleaned_data.items():
            if value == '':
                cleaned_data[key] = None  # 如果不希望空值进入数据库
            else:
                # 移除输入中的空格
                cleaned_data[key] = value.strip()

        return cleaned_data


class TrackerForm(forms.Form):
    action = forms.ChoiceField(choices=[('add', 'Add'), ('delete', 'Delete')], label='Action',required=True)
    group_name = forms.CharField(label='Resource Group Name', required=True,
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}))  # 设置为只读
    tracker_value = forms.CharField(label='Tracker Server ID',required=True,widget=forms.Textarea(attrs={'class': 'form-control', }))

    def clean(self):
        cleaned_data = super().clean()

        # 去除空值
        for key, value in cleaned_data.items():
            if value == '':
                cleaned_data[key] = None  # 如果不希望空值进入数据库
            else:
                # 移除输入中的空格
                cleaned_data[key] = value.strip()

        return cleaned_data

class ZabbixDeleteForm(forms.Form):
    ip_addresses = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter IP addresses, one per line'}),
        label='IP Addresses'
    )
    zabbix_server = forms.ChoiceField(
        choices=[],  # 这里不需要默认值，动态生成
        widget=forms.Select(attrs={'class': 'form-control'})
    )

