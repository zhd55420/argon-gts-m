from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    # 判断field是否有as_widget方法
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    else:
        # 如果field不是表单字段对象，则直接返回
        return field