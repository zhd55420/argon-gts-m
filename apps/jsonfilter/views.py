from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from .forms import JSONInputForm
import json
from django.contrib.auth.decorators import login_required
@login_required(login_url="/login/")
@permission_required('apps_authentication.can_access_json_filter_view', raise_exception=True)
def json_filter_view(request):
    form = JSONInputForm()
    filtered_data = []
    extra_tag_filter = None

    if request.method == 'POST':
        form = JSONInputForm(request.POST)
        if form.is_valid():
            # 获取表单中的 JSON 数据
            json_data = form.cleaned_data['json_data']
            try:
                # 解析 JSON 数据
                data = json.loads(json_data)

                # 过滤 extraTag
                extra_tag_filter = request.POST.get('extra_tag_filter', None)

                # 假设你的 JSON 数据有 result 字段
                if 'result' in data:
                    for item in data['result']:
                        # 检查 connectedStatus == 0 且 streamStatus == 1
                        if item.get('connectedStatus') == 0 and item.get('streamStatus') == 1:
                            # 如果有 extraTag 筛选器，按需过滤
                            if extra_tag_filter:
                                if item.get('extraTag') == extra_tag_filter:
                                    filtered_data.append({
                                        'remark': item.get('remark', ''),
                                        'sourceName': item.get('sourceName', ''),
                                        'urls': item.get('urls', []),
                                        'bw': item.get('bw', {}).get('parsedValue', ''),  # 取 parsedValue
                                        'extraTag': item.get('extraTag', ''),
                                        'streamStatus': item.get('streamStatus', ''),
                                    })


            except json.JSONDecodeError:
                form.add_error('json_data', 'Invalid JSON data.')

    # 获取所有的 unique extraTags
    extra_tags = set([item.get('extraTag') for item in filtered_data if item.get('extraTag')])

    context = {
        'form': form,
        'filtered_data': filtered_data,
        'extra_tags': extra_tags,
        'selected_extra_tag': extra_tag_filter
    }
    return render(request, 'jsonfilter/json_filter.html', context)
