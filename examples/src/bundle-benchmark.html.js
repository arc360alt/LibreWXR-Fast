<!-- SPDX-License-Identifier: MIT -->
<!DOCTYPE html>
<html>
<head>
    <title>LibreWXR - Tile Bundle Benchmark</title>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <link href="https://unpkg.com/leaflet/dist/leaflet.css" rel="stylesheet"/>
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <style>
        /*__VIEWER_CSS__*/

        /* === BUNDLE BENCHMARK PAGE === */
        .bench-panel {
            position: absolute;
            top: var(--space-3);
            left: var(--space-3);
            z-index: var(--z-overlay);
            width: 320px;
            max-width: calc(100vw - 24px);
            background: var(--card-bg);
            border: 1px solid var(--btn-border);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            backdrop-filter: var(--backdrop-blur);
            -webkit-backdrop-filter: var(--backdrop-blur);
            padding: var(--space-3);
            font-size: var(--font-size-sm);
            color: var(--text);
        }
        .bench-panel h2 {
            font-size: var(--font-size-md);
            margin-bottom: var(--space-2);
        }
        .bench-row {
            display: flex;
            align-items: center;
            gap: var(--space-2);
            margin-bottom: var(--space-2);
            flex-wrap: wrap;
        }
        .bench-row label {
            color: var(--text-secondary);
            display: inline-flex;
            align-items: center;
            gap: var(--space-1);
        }
        .bench-btn {
            height: 34px;
            padding: 0 var(--space-4);
            background: var(--accent);
            color: #fff;
            border: none;
            border-radius: var(--radius-sm);
            font-weight: 600;
            cursor: pointer;
            transition: background var(--transition-fast), transform var(--transition-fast);
        }
        .bench-btn:hover { background: var(--accent-hover); }
        .bench-btn:active { transform: scale(0.97); }
        .bench-btn:disabled { opacity: 0.5; cursor: default; }
        .bench-results {
            margin-top: var(--space-2);
            border-top: 1px solid var(--btn-border);
            padding-top: var(--space-2);
        }
        .bench-results table {
            width: 100%;
            border-collapse: collapse;
            font-variant-numeric: tabular-nums;
        }
        .bench-results th, .bench-results td {
            text-align: right;
            padding: 3px 4px;
        }
        .bench-results th:first-child, .bench-results td:first-child { text-align: left; }
        .bench-results thead th {
            color: var(--text-dim);
            font-weight: 600;
            border-bottom: 1px solid var(--btn-border);
        }
        .bench-verdict {
            margin-top: var(--space-2);
            font-weight: 700;
            color: var(--accent);
        }
        .bench-status {
            margin-top: var(--space-2);
            color: var(--text-secondary);
            min-height: 1.2em;
        }
        .bench-play {
            position: absolute;
            bottom: var(--space-3);
            left: 50%;
            transform: translateX(-50%);
            z-index: var(--z-overlay);
            display: flex;
            align-items: center;
            gap: var(--space-2);
            background: var(--card-bg);
            border: 1px solid var(--btn-border);
            border-radius: var(--radius-full);
            box-shadow: var(--shadow-md);
            padding: var(--space-1) var(--space-3);
            font-size: var(--font-size-sm);
            color: var(--text);
        }
        .bench-play button {
            height: 30px;
            padding: 0 var(--space-3);
            border-radius: var(--radius-full);
            border: none;
            background: var(--accent);
            color: #fff;
            font-weight: 600;
            cursor: pointer;
        }
        .bench-play.hidden { display: none; }
    </style>
</head>
<body data-theme="dark">

<div class="toolbar">
    <span class="toolbar-title">LibreWXR</span>
    <!-- #lv-source block: removed in --site builds -->
    <select id="lv-source" aria-label="API source">
        <option value="local">Local (localhost:8080)</option>
        <option value="public">Public (api.librewxr.net)</option>
    </select>
    <!-- /#lv-source -->
    <span style="color:var(--text-secondary)">Tile Bundle Benchmark &mdash; pan/zoom to a viewport, then run.</span>
</div>

<div id="lv-map">
    <div class="bench-panel">
        <h2>Delivery benchmark</h2>
        <div class="bench-row">
            <label>Format
                <select id="b-format">
                    <option value="webp">WebP</option>
                    <option value="png">PNG</option>
                </select>
            </label>
            <label>Size
                <select id="b-size">
                    <option value="256">256</option>
                    <option value="512">512</option>
                </select>
            </label>
        </div>
        <div class="bench-row">
            <label><input type="checkbox" id="b-smooth" checked/> Smoothing</label>
            <label><input type="checkbox" id="b-snow" checked/> Snow</label>
        </div>
        <div class="bench-row">
            <label>Frames
                <select id="b-frames">
                    <option value="all">All (past + nowcast)</option>
                    <option value="6">Latest 6</option>
                    <option value="1">Latest 1</option>
                </select>
            </label>
        </div>
        <button type="button" class="bench-btn" id="b-run">Run benchmark</button>
        <div class="bench-status" id="b-status">Loading catalog&hellip;</div>
        <div class="bench-results" id="b-results" hidden>
            <table>
                <thead>
                    <tr><th>Method</th><th>Requests</th><th>KB</th><th>Wall ms</th></tr>
                </thead>
                <tbody>
                    <tr><td>Individual tiles</td><td id="r-a-req">&ndash;</td><td id="r-a-kb">&ndash;</td><td id="r-a-ms">&ndash;</td></tr>
                    <tr><td>Single bundle</td><td id="r-b-req">&ndash;</td><td id="r-b-kb">&ndash;</td><td id="r-b-ms">&ndash;</td></tr>
                </tbody>
            </table>
            <div class="bench-verdict" id="b-verdict"></div>
        </div>
    </div>

    <div class="bench-play hidden" id="b-play">
        <button type="button" id="b-play-btn">Play</button>
        <span id="b-play-label">&ndash;</span>
    </div>
</div>

<script>
/* SPDX-License-Identifier: MIT
   Standalone benchmark: compares fetching a radar frame's viewport as many
   individual tile requests vs. one LWXB bundle request, then animates the
   bundle-delivered frames on the map. No shared viewer engine. */
(function () {
    'use strict';

    var LVR_API_FIXED = null; // --site build pins this to the public API base

    var API_SOURCES = {
        local: 'http://localhost:8080',
        public: 'https://api.librewxr.net'
    };
    var COLOR = 10;                 // color scheme (not part of the bundle cache key)
    var TILE_CONCURRENCY = 6;       // parallel fetches, both methods
    var BUNDLE_MAGIC = 0x4258574c;  // 'LWXB' little-endian uint32

    var map = L.map('lv-map', { zoomSnap: 1 }).setView([39.83, -98.58], 5);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '&copy; OpenStreetMap'
    }).addTo(map);
    document.getElementById('lv-map').classList.add('lv-basemap-dark');

    var $ = function (id) { return document.getElementById(id); };
    var catalog = null;       // weather-maps.json
    var maxBundleTiles = 256; // from /health, refined below
    var frameLayers = [];     // per-frame L.layerGroup of imageOverlays
    var objectUrls = [];      // tracked for revoke on re-run
    var playTimer = null;
    var playIdx = 0;

    function apiBase() {
        if (LVR_API_FIXED) return LVR_API_FIXED;
        var sel = $('lv-source');
        return API_SOURCES[sel ? sel.value : 'local'] || API_SOURCES.local;
    }

    /* --- slippy tile math --- */
    function lon2tile(lon, z) { return Math.floor((lon + 180) / 360 * Math.pow(2, z)); }
    function lat2tile(lat, z) {
        var r = lat * Math.PI / 180;
        return Math.floor((1 - Math.asinh(Math.tan(r)) / Math.PI) / 2 * Math.pow(2, z));
    }
    function tile2lon(x, z) { return x / Math.pow(2, z) * 360 - 180; }
    function tile2lat(y, z) {
        var n = Math.PI - 2 * Math.PI * y / Math.pow(2, z);
        return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
    }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

    /* Integer-zoom tile rectangle for the current viewport, clamped to the
       world and to maxBundleTiles (shrinks the east/south edge if needed). */
    function viewportRect() {
        var z = Math.round(map.getZoom());
        var b = map.getBounds();
        var n = Math.pow(2, z);
        var x0 = clamp(lon2tile(b.getWest(), z), 0, n - 1);
        var x1 = clamp(lon2tile(b.getEast(), z), 0, n - 1);
        var y0 = clamp(lat2tile(b.getNorth(), z), 0, n - 1);
        var y1 = clamp(lat2tile(b.getSouth(), z), 0, n - 1);
        if (x1 < x0) x1 = x0;
        if (y1 < y0) y1 = y0;
        while ((x1 - x0 + 1) * (y1 - y0 + 1) > maxBundleTiles) {
            if (x1 - x0 >= y1 - y0) x1--; else y1--;
        }
        return { z: z, x0: x0, y0: y0, x1: x1, y1: y1 };
    }

    function opts() {
        return {
            fmt: $('b-format').value,
            size: $('b-size').value,
            ss: ($('b-smooth').checked ? '1' : '0') + '_' + ($('b-snow').checked ? '1' : '0')
        };
    }

    function selectedFrames() {
        var past = (catalog.radar && catalog.radar.past) || [];
        var now = (catalog.radar && catalog.radar.nowcast) || [];
        var all = past.concat(now);
        var pick = $('b-frames').value;
        if (pick === 'all') return all;
        return all.slice(-parseInt(pick, 10));
    }

    function tileUrl(frame, r, o, x, y, cb) {
        return apiBase() + frame.path + '/' + o.size + '/' + r.z + '/' + x + '/' + y +
            '/' + COLOR + '/' + o.ss + '.' + o.fmt + '?cb=' + cb;
    }
    function bundleUrl(frame, r, o, cb) {
        return apiBase() + frame.path + '/bundle/' + o.size + '/' + r.z + '/' +
            r.x0 + '/' + r.y0 + '/' + r.x1 + '/' + r.y1 + '/' + COLOR + '/' + o.ss +
            '.' + o.fmt + '?cb=' + cb;
    }

    /* Run `tasks` (array of () => Promise) with bounded concurrency. */
    function pool(tasks, limit) {
        var i = 0, active = 0, done = 0, results = new Array(tasks.length);
        return new Promise(function (resolve, reject) {
            function next() {
                if (done === tasks.length) return resolve(results);
                while (active < limit && i < tasks.length) {
                    (function (idx) {
                        active++;
                        tasks[idx]().then(function (v) {
                            results[idx] = v; active--; done++; next();
                        }, reject);
                    })(i++);
                }
            }
            next();
        });
    }

    /* --- LWXB bundle unpack --- */
    function unpackBundle(buf, ct) {
        var dv = new DataView(buf);
        if (dv.getUint32(0, true) !== BUNDLE_MAGIC) throw new Error('bad bundle magic');
        var manifestLen = dv.getUint32(8, true);
        var manifest = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 12, manifestLen)));
        var base = 12 + manifestLen;
        var type = manifest.content_type || ct || 'image/png';
        var tiles = manifest.tiles.map(function (t) {
            var blob = new Blob([buf.slice(base + t.o, base + t.o + t.n)], { type: type });
            return { x: t.x, y: t.y, url: URL.createObjectURL(blob) };
        });
        return { manifest: manifest, tiles: tiles };
    }

    /* --- Method A: individual tiles --- */
    function runIndividual(frames, r, o, cb) {
        var tasks = [];
        frames.forEach(function (f) {
            for (var y = r.y0; y <= r.y1; y++) {
                for (var x = r.x0; x <= r.x1; x++) {
                    (function (f, x, y) {
                        tasks.push(function () {
                            return fetch(tileUrl(f, r, o, x, y, cb), { cache: 'no-store' })
                                .then(function (res) { return res.blob(); })
                                .then(function (b) { return b.size; });
                        });
                    })(f, x, y);
                }
            }
        });
        var t0 = performance.now();
        return pool(tasks, TILE_CONCURRENCY).then(function (sizes) {
            var bytes = sizes.reduce(function (a, b) { return a + b; }, 0);
            return { requests: tasks.length, bytes: bytes, ms: performance.now() - t0 };
        });
    }

    /* --- Method B: one bundle per frame --- */
    function runBundle(frames, r, o, cb) {
        var unpacked = new Array(frames.length);
        var tasks = frames.map(function (f, idx) {
            return function () {
                return fetch(bundleUrl(f, r, o, cb), { cache: 'no-store' })
                    .then(function (res) {
                        return res.arrayBuffer().then(function (buf) {
                            unpacked[idx] = unpackBundle(buf, res.headers.get('content-type'));
                            return buf.byteLength;
                        });
                    });
            };
        });
        var t0 = performance.now();
        return pool(tasks, TILE_CONCURRENCY).then(function (lens) {
            var bytes = lens.reduce(function (a, b) { return a + b; }, 0);
            return {
                requests: frames.length, bytes: bytes, ms: performance.now() - t0,
                frames: frames, unpacked: unpacked, rect: r
            };
        });
    }

    /* --- Render bundle-delivered frames as imageOverlays --- */
    function renderFrames(result) {
        stopPlay();
        frameLayers.forEach(function (g) { map.removeLayer(g); });
        frameLayers = [];
        objectUrls.forEach(function (u) { URL.revokeObjectURL(u); });
        objectUrls = [];

        var z = result.rect.z;
        result.unpacked.forEach(function (up) {
            var group = L.layerGroup();
            up.tiles.forEach(function (t) {
                objectUrls.push(t.url);
                var bounds = [
                    [tile2lat(t.y + 1, z), tile2lon(t.x, z)],
                    [tile2lat(t.y, z), tile2lon(t.x + 1, z)]
                ];
                L.imageOverlay(t.url, bounds, { opacity: 0, interactive: false }).addTo(group);
            });
            group.addTo(map);
            frameLayers.push(group);
        });

        playIdx = frameLayers.length - 1;
        showFrame(playIdx, result.frames);
        $('b-play').classList.remove('hidden');
    }

    function setGroupOpacity(group, v) {
        group.eachLayer(function (l) { l.setOpacity(v); });
    }
    function showFrame(idx, frames) {
        frameLayers.forEach(function (g, i) { setGroupOpacity(g, i === idx ? 0.8 : 0); });
        var t = frames[idx] && frames[idx].time;
        $('b-play-label').textContent = t
            ? new Date(t * 1000).toLocaleTimeString() + '  (' + (idx + 1) + '/' + frames.length + ')'
            : (idx + 1) + '/' + frames.length;
    }
    function startPlay(frames) {
        if (frameLayers.length < 2) return;
        $('b-play-btn').textContent = 'Pause';
        playTimer = setInterval(function () {
            playIdx = (playIdx + 1) % frameLayers.length;
            showFrame(playIdx, frames);
        }, 500);
    }
    function stopPlay() {
        if (playTimer) { clearInterval(playTimer); playTimer = null; }
        var btn = $('b-play-btn');
        if (btn) btn.textContent = 'Play';
    }

    /* --- Orchestration --- */
    function fmtKB(bytes) { return (bytes / 1024).toFixed(1); }

    function runBenchmark() {
        if (!catalog) return;
        var frames = selectedFrames();
        if (!frames.length) { $('b-status').textContent = 'No frames in catalog.'; return; }
        var r = viewportRect();
        var o = opts();
        var tilesPerFrame = (r.x1 - r.x0 + 1) * (r.y1 - r.y0 + 1);
        var cb = Math.random().toString(36).slice(2);

        $('b-run').disabled = true;
        $('b-results').hidden = true;
        $('b-status').textContent = 'Zoom ' + r.z + ', ' + tilesPerFrame + ' tiles/frame x ' +
            frames.length + ' frames. Fetching individually…';

        runIndividual(frames, r, o, cb + 'a').then(function (a) {
            $('b-status').textContent = 'Individual done in ' + a.ms.toFixed(0) +
                ' ms. Fetching as bundles…';
            return runBundle(frames, r, o, cb + 'b').then(function (b) {
                $('r-a-req').textContent = a.requests;
                $('r-a-kb').textContent = fmtKB(a.bytes);
                $('r-a-ms').textContent = a.ms.toFixed(0);
                $('r-b-req').textContent = b.requests;
                $('r-b-kb').textContent = fmtKB(b.bytes);
                $('r-b-ms').textContent = b.ms.toFixed(0);
                var speed = (a.ms / b.ms);
                $('b-verdict').textContent = 'Bundle: ' + speed.toFixed(1) + '× faster wall time, ' +
                    (a.requests - b.requests) + ' fewer requests.';
                $('b-results').hidden = false;
                $('b-status').textContent = 'Rendering bundle frames…';
                renderFrames(b);
                $('b-status').textContent = 'Done. Press Play to animate.';
                $('b-run').disabled = false;
            });
        }).catch(function (e) {
            $('b-status').textContent = 'Error: ' + e.message;
            $('b-run').disabled = false;
        });
    }

    function loadCatalog() {
        $('b-status').textContent = 'Loading catalog…';
        fetch(apiBase() + '/public/weather-maps.json', { cache: 'no-store' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                catalog = data;
                return fetch(apiBase() + '/health', { cache: 'no-store' })
                    .then(function (r) { return r.json(); })
                    .then(function (h) {
                        if (h && h.tile_bundles && h.tile_bundles.max_tiles) {
                            maxBundleTiles = h.tile_bundles.max_tiles;
                        }
                    }, function () {});
            })
            .then(function () {
                var past = (catalog.radar && catalog.radar.past) || [];
                var now = (catalog.radar && catalog.radar.nowcast) || [];
                $('b-status').textContent = past.length + ' past + ' + now.length +
                    ' nowcast frames. Pan/zoom, then Run benchmark.';
            })
            .catch(function (e) {
                $('b-status').textContent = 'Catalog load failed: ' + e.message;
            });
    }

    $('b-run').addEventListener('click', runBenchmark);
    $('b-play-btn').addEventListener('click', function () {
        if (playTimer) stopPlay();
        else startPlay(selectedFrames());
    });
    var srcSel = $('lv-source');
    if (srcSel) {
        var loc = window.location;
        srcSel.value = (loc.protocol === 'file:' || loc.hostname === 'localhost' ||
            loc.hostname === '127.0.0.1') ? 'local' : 'public';
        srcSel.addEventListener('change', loadCatalog);
    }
    loadCatalog();
})();
</script>
</body>
</html>
