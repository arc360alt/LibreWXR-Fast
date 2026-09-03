# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Joshua Kimsey
"""Single-request radar tile bundles.

Renders every tile of one frame within a viewport (a tile rectangle at a
single zoom) and concatenates them into one small archive so a web client
makes a single HTTP request instead of one per tile.

Container format ``LWXB`` v1 (little-endian, no compression — the tile
payloads are already-compressed PNG/WebP):

    bytes  0..3    magic  b"LWXB"
    byte   4       version (1)
    bytes  5..7    reserved (0)
    bytes  8..11   uint32  manifest length M
    bytes  12..12+M UTF-8 JSON manifest
    then           concatenated tile payloads

The JSON manifest carries ``tiles`` as ``{"x", "y", "o", "n"}`` records
where ``o`` is the payload's byte offset *within the payload region*
(i.e. relative to ``12 + M``) and ``n`` its length.  Fully transparent
tiles are omitted entirely — the client leaves those blank.
"""
import json
import struct

from librewxr.api.conditional import compute_etag
from librewxr.config import settings
from librewxr.tiles.cache import CachedRender
from librewxr.tiles.renderer import compute_tile_geometry, present_tile

BUNDLE_MAGIC = b"LWXB"
BUNDLE_VERSION = 1
BUNDLE_CONTENT_TYPE = "application/vnd.librewxr.tilebundle"

_HEADER_STRUCT = struct.Struct("<4sB3xI")  # magic, version, 3 pad bytes, manifest len


def _content_type_for(ext: str) -> str:
    return "image/webp" if ext == "webp" else "image/png"


def build_tile_bundle(
    *,
    frame_regions,
    timestamp: int,
    z: int,
    x_min: int,
    y_min: int,
    x_max: int,
    y_max: int,
    tile_size: int = 256,
    smooth: bool = False,
    snow: bool = False,
    color: int = 0,
    ext: str = "webp",
    nwp_chain=None,
    enabled_regions: list[str] | None = None,
    nowcast_blend: float | None = None,
    precip_mask=None,
    tile_cache=None,
) -> bytes:
    """Render the tile rectangle for one frame and pack it into an ``LWXB`` bundle.

    The geometry and present caches are keyed identically to
    ``routes.radar_tile`` so a warm single-tile cache accelerates the
    bundle and the bundle's renders warm the single-tile path in turn.
    """
    payloads: list[bytes] = []
    entries: list[dict] = []
    offset = 0

    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            geom_key = (timestamp, z, x, y, tile_size, smooth, snow)
            geom = tile_cache.get(geom_key) if tile_cache is not None else None
            if geom is None:
                geom = compute_tile_geometry(
                    frame_regions=frame_regions,
                    z=z, x=x, y=y,
                    tile_size=tile_size,
                    smooth=smooth,
                    snow=snow,
                    nwp_chain=nwp_chain,
                    enabled_regions=enabled_regions,
                    frame_timestamp=timestamp,
                    nowcast_blend=nowcast_blend,
                    precip_mask=precip_mask,
                )
                if tile_cache is not None:
                    tile_cache.put(geom_key, geom)

            if geom.is_transparent:
                continue

            present_key = (
                timestamp, z, x, y, tile_size, smooth, snow,
                color, ext, settings.webp_quality,
            )
            cached = tile_cache.get(present_key) if tile_cache is not None else None
            if isinstance(cached, CachedRender):
                data = cached.data
            else:
                data = present_tile(
                    geom, color_scheme=color, fmt=ext, arrow_style="",
                )
                if tile_cache is not None:
                    tile_cache.put(
                        present_key,
                        CachedRender(data=data, etag=compute_etag(data)),
                    )

            payloads.append(data)
            entries.append({"x": x, "y": y, "o": offset, "n": len(data)})
            offset += len(data)

    manifest = {
        "v": BUNDLE_VERSION,
        "timestamp": timestamp,
        "zoom": z,
        "tile_size": tile_size,
        "format": ext,
        "content_type": _content_type_for(ext),
        "x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max,
        "tiles": entries,
    }
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode("utf-8")

    parts = [
        _HEADER_STRUCT.pack(BUNDLE_MAGIC, BUNDLE_VERSION, len(manifest_bytes)),
        manifest_bytes,
    ]
    parts.extend(payloads)
    return b"".join(parts)
