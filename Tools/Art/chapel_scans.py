"""Bake downloadable CC0 photogrammetry to UE-ready sRGB, AO/roughness and DX normal maps."""
import hashlib
import json
from pathlib import Path
import urllib.request

import numpy as np
from PIL import Image

# Mix the source color toward luminance before the instance adds its church-stone tint.
FAMILIES = {
    'Paving': ('rock_tile_floor', .25, .70),
    'Choir': ('patterned_paving', .43, .64),
    'Masonry': ('large_sandstone_blocks', .58, .77),
    'Dressed': ('rock_surface', .46, .62),
}


def source_file(cache, asset, channel, hashes):
    filename = f'{asset}_{channel}_2k.jpg'
    path = cache / filename
    expected = hashes[filename]
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
        return path
    url = f'https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/{asset}/{filename}'
    request = urllib.request.Request(url, headers={'User-Agent': 'SoulBreak environment authoring/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Unexpected source digest for {filename}')
    path.write_bytes(data)
    return path


def bake_stone(out):
    """Keep the licensed source cache outside Content. Only baked assets go into the game."""
    cache = out.parent / 'StoneScans'
    cache.mkdir(parents=True, exist_ok=True)
    hashes = json.loads(Path(__file__).with_name('chapel_scan_hashes.json').read_text())
    for family, (asset, saturation, slope) in FAMILIES.items():
        def load(channel):
            path = source_file(cache, asset, channel, hashes)
            return np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.
        def save(channel, data):
            image = np.uint8(np.clip(data, 0., 1.) * 255. + .5)
            Image.fromarray(image).save(out / f'T_{family}_{channel}.png', compress_level=3)
        rgb = load('diff')
        linear = np.where(rgb < .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
        lum = linear @ np.array([.2126, .7152, .0722], dtype=np.float32)
        toned = linear * saturation + lum[..., None] * (1. - saturation)
        # Remove acquisition exposure differences, preserving relative stone and joint values.
        target = {'Paving': .19, 'Choir': .16, 'Masonry': .22, 'Dressed': .24}[family]
        toned = np.clip(toned * target / max(.01, np.median(lum)), 0., 1.)
        srgb = np.where(toned < .0031308, toned * 12.92, 1.055 * toned ** (1 / 2.4) - .055)
        save('C', srgb)
        normal = load('nor_dx') * 2. - 1.
        normal[..., :2] *= slope
        normal /= np.maximum(.001, np.linalg.norm(normal, axis=-1, keepdims=True))
        save('N', normal * .5 + .5)
        arm = load('arm')
        save('M', np.stack((np.ones_like(lum), .30 + .70 * arm[..., 1], arm[..., 0]), -1))
    Image.new('RGB', (4, 4), 'white').save(out / 'T_Neutral_C.png')
