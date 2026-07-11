#!/usr/bin/env python3
"""
Generate hair-color variants (black, gray, brown, blond, red, blue, green,
purple, pink) from a `*_var_white.png` source sprite, for inspection in
draft/ before being placed into the tileset.

Workflow: draw a new hairstyle's `..._var_white.png`, then run this
script against it (or against the whole appearance/hair folder to
catch every white sprite missing its color set). Generated files land
in a draft folder for review -- nothing under dda/gfx is touched.

Colors are produced via HSL colorize: each source pixel's grayscale
value becomes the lightness channel (L), recombined with a fixed
hue/saturation per target color. Pixels with value <= OUTLINE_THRESHOLD
(the black outline + its anti-aliasing halo) are forced to pure black
instead of being colorized, matching the rest of this tileset's outline
convention.

blue/green/purple/pink are this tileset's own invented "dye" colors, so
their params reproduce prior output exactly. black/gray/brown/blond/red
are original hand-painted colors in the existing hairstyles -- their
params were fit (median H/S/scale) from all 10 existing styles that
have every color, so new styles get a close visual match rather than a
pixel-exact one (avg channel error ~10-19/255 against the real thing).

Usage:
    # single sprite
    python3 tools/generate_hair_colors.py path/to/..._var_white.png

    # every *_var_white.png in a folder
    python3 tools/generate_hair_colors.py path/to/appearance/hair/

    # custom output location (default: draft/hair_color_preview)
    python3 tools/generate_hair_colors.py path/to/hair/ -o draft/my_preview
"""

import argparse
import colorsys
import glob
import os

import pyvips

# Locked-in parameters. H in degrees/360, S 0-1, scale compresses/maps
# lightness (value/255 * scale) before the HLS conversion.
#
# blue/green/purple/pink: agreed 2026-07-11, invented "dye" colors.
# black/gray/brown/blond/red: fit 2026-07-11 from median H/S/scale across
# all 10 existing hairstyles that already have these colors.
COLOR_PARAMS = {
    'blue':   {'h': 215 / 360, 's': 0.55, 'scale': 0.85},
    'green':  {'h': 125 / 360, 's': 0.55, 'scale': 0.85},
    'purple': {'h': 275 / 360, 's': 0.55, 'scale': 0.85},
    'pink':   {'h': 325 / 360, 's': 0.55, 'scale': 0.85},
    'black':  {'h': 0 / 360,   's': 0.0,   'scale': 0.218},
    'gray':   {'h': 0 / 360,   's': 0.0,   'scale': 0.565},
    'brown':  {'h': 34 / 360,  's': 0.345, 'scale': 0.383},
    'blond':  {'h': 46.2 / 360, 's': 0.522, 'scale': 0.609},
    'red':    {'h': 13.0 / 360, 's': 0.558, 'scale': 0.436},
}
OUTLINE_THRESHOLD = 34


def colorize(src_path: str, h: float, s: float, scale: float, out_path: str) -> None:
    im = pyvips.Image.new_from_file(src_path)
    w, height, bands = im.width, im.height, im.bands
    buf = bytearray(im.write_to_memory())

    for i in range(0, len(buf), bands):
        alpha = buf[i + 3] if bands == 4 else 255
        if alpha == 0:
            continue
        value = buf[i]  # source is grayscale: R == G == B
        if value <= OUTLINE_THRESHOLD:
            buf[i], buf[i + 1], buf[i + 2] = 0, 0, 0
            continue
        lightness = (value / 255.0) * scale
        r, g, b = colorsys.hls_to_rgb(h, lightness, s)
        buf[i], buf[i + 1], buf[i + 2] = round(r * 255), round(g * 255), round(b * 255)

    out = pyvips.Image.new_from_memory(bytes(buf), w, height, bands, 'uchar')
    out.pngsave(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'source', help='a *_var_white.png file, or a folder to scan for them')
    parser.add_argument(
        '-o', '--out-dir', default='draft/hair_color_preview',
        help='where to write generated previews (default: draft/hair_color_preview)')
    args = parser.parse_args()

    if os.path.isdir(args.source):
        white_files = sorted(glob.glob(os.path.join(args.source, '*_var_white.png')))
    elif args.source.endswith('_var_white.png'):
        white_files = [args.source]
    else:
        parser.error('source must be a *_var_white.png file or a directory')
        return

    if not white_files:
        print(f'no *_var_white.png files found at {args.source}')
        return

    os.makedirs(args.out_dir, exist_ok=True)

    count = 0
    for src in white_files:
        for color, params in COLOR_PARAMS.items():
            out_name = os.path.basename(src).replace('_var_white.png', f'_var_{color}.png')
            out_path = os.path.join(args.out_dir, out_name)
            colorize(src, params['h'], params['s'], params['scale'], out_path)
            count += 1
            print(f'wrote {out_path}')

    print(f'generated {count} preview PNGs in {args.out_dir}')


if __name__ == '__main__':
    main()
