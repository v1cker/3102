#!/usr/bin/env python
# coding=utf-8

"""
Copyright (c) 2014 Fooying (http://www.fooying.com)
Mail:f00y1n9[at]gmail.com
"""

import os
import yaml
import gevent
import logging

from gevent.monkey import patch_all

from core.data import kb
from core.data import conf
from comm.coroutine import WorkerPool

patch_all()
logger = logging.getLogger('3102')


class PluginController(object):
    def __init__(self):
        self.exit = False
        self.wp = WorkerPool()
        self.plugin_path = conf.settings.PLUGIN_PATH

    def plugin_init(self):
        """
        初始化插件
        """
        plugin_list = os.listdir(self.plugin_path)
        for plugin in plugin_list:
            plugin_config_path = os.path.join(
                self.plugin_path, plugin, 'config.yaml'
            )

            if os.path.exists(plugin_config_path):
                with open(plugin_config_path) as f:
                    try:
                        conf.plugins[plugin] = yaml.load(f)
                    except Exception:
                        logger.exception('load %s\'s config fail!' % plugin)
                    else:
                        if conf.plugins[plugin]['enable']:
                            self.__register_plugin(plugin)
                            self.__classify_plugin(plugin)
                        else:
                            conf.plugins.pop(plugin)

    def __register_plugin(self, plugin):
        """
        注册插件
        """
        registered_plugin = kb.plugins[plugin] = {}
        registered_plugin['name'] = plugin
        try:
            registered_plugin['handle'] = self.__load_plugin(plugin)
        except Exception:
            logger.exception('register plugin failed!')

    def __classify_plugin(self, plugin):
        """
        归类插件
        """
        inputs = conf.plugins[plugin]['input']
        for inp in inputs:
            if inp in conf.settings.ALLOW_INPUT:
                conf.reg_plugins[inp].add(plugin)

    def __load_plugin(self, plugin_name):
        """
        动态载入插件模块函数
        """
        _plugin = None
        plugin_path = 'plugins.%s.work' % plugin_name
        try:
            _plugin = __import__(plugin_path, fromlist='*')
        except Exception:
            logger.exception(
                'plugin[%s] __load_plugin failed!' % plugin_name
            )
        return _plugin

    def start(self):
        while not self.exit:
            try:
                target = self.wp.target_queue.get_nowait()
            except gevent.queue.Empty:
                pass
            else:
                self._run_plugin_by_type(target)

    def _run_plugin_by_type(self, target):
        domain_type = target.get('domain_type')
        if domain_type in conf.settings.ALLOW_INPUT:
            for plugin in conf.reg_plugins[domain_type]:
                _plugin = getattr(kb.plugins[plugin]['handle'], plugin)()
                self.wp.add_job(getattr(_plugin, 'start'), **target)
            self.wp.run()

    def exit(self):
        self.exit = True
