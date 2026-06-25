from typing import Callable, Any

from eva.brain.abc import OutputChannel
from eva.face.abc import ImmediatePlaybackTTS
from eva.face.mute_group import NULL_MUTE_GROUP
from eva.face.tts_helpers import ImmediatePlaybackTTSOutput
from eva.plugin_loader.abc import PluginManager
from eva.plugin_loader.run_operation import call_all_as_wrappers

name = 'plugin_local_output_tts'
version = '0.2.0'


def create_local_outputs(
        nxt: Callable,
        prev: list[OutputChannel],
        pm: PluginManager,
        settings: dict[str, Any],
        *args,
        **kwargs
):
    if settings.get('type', None) == 'tts':
        ttss: list[ImmediatePlaybackTTS] = call_all_as_wrappers(
            pm.get_operation_sequence('get_immediate_playback_tts_engines'),
            [],
            pm,
            selector=settings.get('profile_selector', None),
        )

        mute_group = kwargs.get('mute_group', NULL_MUTE_GROUP)

        for tts in ttss:
            prev.append(
                ImmediatePlaybackTTSOutput(tts, mute_group)
            )

    return nxt(prev, pm, settings, *args, **kwargs)
