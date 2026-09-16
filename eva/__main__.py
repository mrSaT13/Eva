from os import environ
from os.path import dirname

from eva.brain.brain_plugin import BrainPlugin
from eva.compatibility.compatibility_plugin import OriginalCompatibilityPlugin
from eva.plugin_loader.core_plugins import ConfigPlugin, PluginDiscoveryPlugin
from eva.plugin_loader.core_plugins.logging import LoggingPlugin
from eva.plugin_loader.file_patterns import register_variable, substitute_pattern
from eva.plugin_loader.launcher import launch_application

register_variable('eva_path', dirname(__file__))
register_variable('eva_home', environ.get(
    'EVA_HOME', list(substitute_pattern('{user_home}/eva'))))

launch_application(
    [
        ConfigPlugin(template_paths=('{eva_path}/config_templates',)),
        PluginDiscoveryPlugin(),
        LoggingPlugin(),
        BrainPlugin(),
        OriginalCompatibilityPlugin(),
    ],
    canonical_launch_command='python -m eva',
)
