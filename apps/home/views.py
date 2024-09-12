# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import requests
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseNotFound
from django.template import loader, TemplateDoesNotExist
from django.urls import reverse, resolve, Resolver404
from django.shortcuts import render


@login_required(login_url="/login/")
def index(request):
    context = {'segment': 'index'}

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def pages(request):
    context = {}
    try:
        # 提取 URL 的完整路径并尝试解析
        path = request.path.strip('/')
        if not path:
            # 如果路径为空，则加载首页
            return HttpResponse(loader.get_template('home/index.html').render(context, request))

        # 如果是 'admin'，重定向到 Django Admin 界面
        if path == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))

        # 动态解析 URL，并转发请求到相应的视图
        try:
            # 动态解析整个路径
            resolver_match = resolve('/' + path + '/')
            view_func = resolver_match.func  # 获取视图函数
            return view_func(request)  # 动态调用视图函数
        except Resolver404:
            # 如果没有找到匹配的视图，返回 404 页面
            html_template = loader.get_template('home/page-404.html')
            return HttpResponseNotFound(html_template.render(context, request))

    except TemplateDoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        print(f"An error occurred: {e}")
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

# 代理Zabbix页面的视图

