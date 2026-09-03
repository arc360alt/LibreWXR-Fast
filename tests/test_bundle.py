# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Joshua Kimsey
import asyncio
import io
import json
import struct
import time

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

pytestmark = pytest.mark.api

from librewxr.api import routes
from librewxr.config import settings
from librewxr.data.store import FrameStore, RadarFrame
from librewxr.tiles.bundle import BUNDLE_CONTENT_TYPE, BUNDLE_MAGIC
from librewxr.tiles.cache import TileCache
from librewxr.tiles.coordinates import COMPOSITE_HEIGHT, COMPOSITE_WIDTH


# z=4 tiles over the central US.
_Z, _X0, _Y0, _X1, _Y1 = 4, 3, 5, 4, 6

_GLOBALS = (
    "frame_store", "tile_cache", "ecmwf_grid", "tile_warmer", "nowcast_store",
    "nwp_chain", "precip_mask", "start_time", "enabled_regions",
)


@pytest.fixture(scope="module")
def client():
    # Save/restore the router's module globals so this file's wiring never
    # leaks into other test modules (the suite shares one ``routes`` module).
    saved = {name: getattr(routes, name, None) for name in _GLOBALS}

    store = FrameStore(max_frames=12)
    cache = TileCache(max_mb=20)
    ts = int(time.time() // 300) * 300
    ts_prev = ts - 600

    # Fill the whole USCOMP composite so every tile overlapping CONUS is
    # non-transparent — the bundle's ``tiles`` list is then guaranteed
    # non-empty for a central-US rectangle.
    data = np.full((COMPOSITE_HEIGHT, COMPOSITE_WIDTH), 128, dtype=np.uint8)
    asyncio.run(store.add_frame(RadarFrame(timestamp=ts, regions={"USCOMP": data})))
    asyncio.run(store.add_frame(RadarFrame(timestamp=ts_prev, regions={"USCOMP": data})))

    routes.frame_store = store
    routes.tile_cache = cache
    routes.ecmwf_grid = None
    routes.tile_warmer = None
    routes.nowcast_store = None
    routes.nwp_chain = None
    routes.precip_mask = None
    routes.start_time = time.time()
    routes.enabled_regions = ["USCOMP"]

    app = FastAPI()
    app.include_router(routes.router)
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, ts, ts_prev
    finally:
        for name, value in saved.items():
            setattr(routes, name, value)


def _url(ts, z=_Z, x0=_X0, y0=_Y0, x1=_X1, y1=_Y1, color=10, ss="1_1", ext="webp"):
    return f"/v2/radar/{ts}/bundle/256/{z}/{x0}/{y0}/{x1}/{y1}/{color}/{ss}.{ext}"


def _parse(body: bytes) -> tuple[dict, bytes]:
    assert body[:4] == BUNDLE_MAGIC
    version, manifest_len = struct.unpack_from("<B3xI", body, 4)
    assert version == 1
    manifest = json.loads(body[12:12 + manifest_len].decode("utf-8"))
    return manifest, body[12 + manifest_len:]


class TestBundleEndpoint:
    def test_container_shape(self, client):
        c, ts, _ = client
        resp = c.get(_url(ts))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == BUNDLE_CONTENT_TYPE
        assert resp.headers["x-frame-timestamp"] == str(ts)

        manifest, payload = _parse(resp.content)
        assert manifest["zoom"] == _Z
        assert manifest["format"] == "webp"
        assert (manifest["x_min"], manifest["y_min"]) == (_X0, _Y0)
        assert len(manifest["tiles"]) >= 1

        for entry in manifest["tiles"]:
            assert _X0 <= entry["x"] <= _X1
            assert _Y0 <= entry["y"] <= _Y1
            blob = payload[entry["o"]:entry["o"] + entry["n"]]
            assert len(blob) == entry["n"]
            img = Image.open(io.BytesIO(blob))
            assert img.size == (256, 256)

    def test_payload_offsets_are_contiguous(self, client):
        c, ts, _ = client
        manifest, payload = _parse(c.get(_url(ts)).content)
        cursor = 0
        for entry in manifest["tiles"]:
            assert entry["o"] == cursor
            cursor += entry["n"]
        assert cursor == len(payload)

    def test_timestamp_zero_resolves_latest(self, client):
        c, ts, _ = client
        resp = c.get(_url(0))
        assert resp.status_code == 200
        assert resp.headers["x-frame-timestamp"] == str(ts)

    def test_historical_frame_long_cache(self, client):
        c, _, ts_prev = client
        resp = c.get(_url(ts_prev))
        assert resp.status_code == 200
        assert "max-age=7200" in resp.headers["cache-control"]

    def test_latest_frame_short_cache(self, client):
        c, ts, _ = client
        resp = c.get(_url(ts))
        assert "max-age=300" in resp.headers["cache-control"]

    def test_etag_304(self, client):
        c, ts, _ = client
        first = c.get(_url(ts))
        etag = first.headers["etag"]
        again = c.get(_url(ts), headers={"If-None-Match": etag})
        assert again.status_code == 304
        assert again.content == b""

    def test_missing_frame_404(self, client):
        c, _, _ = client
        assert c.get(_url(9999999999)).status_code == 404

    def test_rectangle_over_budget_400(self, client, monkeypatch):
        c, ts, _ = client
        monkeypatch.setattr(settings, "bundle_max_tiles", 2)
        resp = c.get(_url(ts))
        assert resp.status_code == 400

    def test_inverted_rectangle_400(self, client):
        c, ts, _ = client
        resp = c.get(_url(ts, x0=5, x1=3))
        assert resp.status_code == 400

    def test_out_of_range_400(self, client):
        c, ts, _ = client
        resp = c.get(_url(ts, z=2, x0=0, y0=0, x1=9, y1=1))
        assert resp.status_code == 400

    def test_disabled_503(self, client, monkeypatch):
        c, ts, _ = client
        monkeypatch.setattr(settings, "bundle_enabled", False)
        assert c.get(_url(ts)).status_code == 503

    def test_bundle_tiles_match_individual_renders(self, client):
        c, ts, _ = client
        manifest, payload = _parse(c.get(_url(ts, ss="1_1", color=10)).content)
        for entry in manifest["tiles"]:
            single = c.get(
                f"/v2/radar/{ts}/256/{_Z}/{entry['x']}/{entry['y']}/10/1_1.webp"
            )
            assert single.status_code == 200
            assert payload[entry["o"]:entry["o"] + entry["n"]] == single.content
