"""
Плагин для получения изображений из Home Assistant.
Снимки камер, скриншоты, графики.
"""

import os
import time
from logging import getLogger
from typing import Any

from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('ha_images')


class HAImagesPlugin(MagicPlugin):
    name = 'ha_images'
    version = '1.0.0'

    config: dict[str, Any] = {
        "ha_url": "",
        "ha_token": "",
        "cache_dir": os.path.expanduser("~/eva/image_cache"),
        "cache_ttl": 300,
    }

    def _get_cache_path(self, entity_id: str) -> str:
        cache_dir = self.config['cache_dir']
        os.makedirs(cache_dir, exist_ok=True)
        safe_name = entity_id.replace('.', '_').replace('/', '_')
        return os.path.join(cache_dir, f"{safe_name}_{int(time.time())}.jpg")

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter, HTTPException
        from fastapi.responses import FileResponse
        import httpx

        r: APIRouter = router
        plugin = self

        def _get_ha():
            url = plugin.config.get('ha_url', '')
            token = plugin.config.get('ha_token', '')
            if url and token:
                return url, token
            # Fallback: ищем в automations
            try:
                import yaml
                config_dir = os.path.expanduser('~/eva/config')
                fpath = os.path.join(config_dir, 'automations.yaml')
                if os.path.exists(fpath):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        u = data.get('ha_url', '')
                        t = data.get('ha_token', '')
                        if u and t:
                            return u, t
            except Exception:
                pass
            return None, None

        @r.get('/cameras')
        async def list_cameras():
            ha_url, ha_token = _get_ha()
            if not ha_url or not ha_token:
                return []

            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        f"{ha_url}/api/states",
                        headers={"Authorization": f"Bearer {ha_token}"},
                        timeout=10
                    )
                    if res.status_code == 200:
                        return [
                            {"entity_id": s.get("entity_id"), "name": s.get("attributes", {}).get("friendly_name", s.get("entity_id"))}
                            for s in res.json() if s.get("entity_id", "").startswith("camera.")
                        ]
                    return []
            except Exception:
                return []

        @r.get('/camera/{entity_id}')
        async def get_camera_snapshot(entity_id: str):
            ha_url, ha_token = _get_ha()
            if not ha_url or not ha_token:
                raise HTTPException(503, "HA не настроен")
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        f"{ha_url}/api/camera_proxy/{entity_id}",
                        headers={"Authorization": f"Bearer {ha_token}"},
                        timeout=10
                    )
                    if res.status_code == 200:
                        cache_path = plugin._get_cache_path(entity_id)
                        with open(cache_path, 'wb') as f:
                            f.write(res.content)
                        return FileResponse(cache_path, media_type="image/jpeg")
                    raise HTTPException(res.status_code, f"HA ошибка: {res.status_code}")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(500, str(e))
