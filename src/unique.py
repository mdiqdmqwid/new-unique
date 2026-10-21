import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter
from PIL.TiffImagePlugin import IFDRational
import asyncio, random, os, io, curl_cffi, ffmpeg, platform, base64, tempfile, string, shutil, time, math, subprocess, traceback, datetime, re, struct, uuid, threading, json, configs
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ffmpeg._run import Error


FFMPEG_PATH = "ffmpeg" if platform.system() in ["Darwin", "Linux"] else str(configs.ROOT_PATH / "ffmpeg/bin/ffmpeg.exe")
FFPROBE_PATH = "ffprobe" if platform.system() in ["Darwin", "Linux"] else str(configs.ROOT_PATH / "ffmpeg/bin/ffprobe.exe")
TEMP_PATH = configs.ROOT_PATH / "temp"

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


PHOTO_LAYERS = {
    "PhotoLayer": {
        "name": "Фото",
        "image": "Photo",
        "color": "#4A89FF0D",
        "border_color": "#4A89FF",
        "params": {
            "method": {"name": "Метод получения", "default": "Фоны софта", "type": "dropdown", "options": ["Фоны софта", "Генерировать", "Локальные файлы"]},
            "source": {"name": "Путь к папке/фото", "type": "file", "visible": "method=Локальные файлы"},
            "opacity": {"name": "Непрозрачность", "type": "number", "min": 1, "max": 100, "step": 1, "default": 100},
            "round": {"name": "Закругление", "type": "number", "min": 0, "max": 50, "step": 1, "default": 0},
            "border": {"name": "Обводка", "type": "number", "min": 0, "max": 50, "step": 1, "default": 0},
            "border_color": {"name": "Цвет обводки", "type": "color", "default": "#FFFFFF", "visible": "border>0"},
            "chromakey": {"name": "Хромакей", "type": "checkbox", "default": False},
            "chromakey_color": {"name": "Хромакей", "type": "color", "default": "#00FF00", "visible": "chromakey=true"},
            "chromakey_tolerance": {"name": "Сила хромакея", "type": "number", "min": 0, "max": 255, "step": 1, "default": 60, "visible": "chromakey=true"},
            "random_position": {"name": "Рандомное размещение", "type": "position"}
        }
    },
    "BlurLayer": {
        "name": "Размытие",
        "image": "Noise",
        "color": "#FFDF7E0D",
        "border_color": "#FFDF7E",
        "params": {
            "intensity": {"name": "Интенсивность", "type": "number", "min": 1, "max": 100,"step": 1, "default": 1},
            "feather": {"name": "Растушёвка", "type": "number", "min": 0, "max": 100,"step": 1, "default": 1},
        }
    },
    "SnowLayer": {
        "name": "Снег",
        "image": "Noise",
        "color": "#DF7EFF0D",
        "border_color": "#DF7EFF",
        "params": {
            "snow_count": {"name": "Количество", "type": "number", "min": 1, "max": 500, "step": 1, "default": 1},
            "snow_size": {"name": "Размер", "type": "number", "min": 1, "max": 100, "step": 1, "default": 1},
            "random_position": {"name": "Рандомное размещение", "type": "position"}
        }
    },
    "NoiseLayer": {
        "name": "Шум",
        "image": "Noise",
        "color": "#DF7EFF0D",
        "border_color": "#DF7EFF",
        "params": {
            "noise_intensity": {"name": "Интенсивность шума", "type": "number", "min": 1, "max": 100, "step": 1, "default": 1},
            "random_position": {"name": "Рандомное размещение", "type": "position"}
        }
    },
    "LinesLayer": {
        "name": "Линии",
        "image": "Noise",
        "color": "#DF7EFF0D",
        "border_color": "#DF7EFF",
        "params": {
            "line_thickness": {"name": "Толщина", "type": "number", "min": 1, "max": 20, "step": 1, "default": 1},
            "line_width": {"name": "Размер", "type": "number", "min": 1, "max": 20, "step": 1, "default": 1},
            "random_position": {"name": "Рандомное размещение", "type": "position"}
        }
    },
    "EmojiLayer": {
        "name": "Эмодзи",
        "image": "Noise",
        "color": "#DF7EFF0D",
        "border_color": "#DF7EFF",
        "params": {
            "emoji_count": {"name": "Количество", "type": "number", "min": 1, "max": 100, "step": 1, "default": 1},
            "emoji_scale_factor": {"name": "Масштаб", "type": "number", "min": 0.1, "max": 10, "step": 0.1, "default": 1},
            "emoji_opacity": {"name": "Непрозрачность", "type": "number", "min": 1, "max": 100, "step": 1, "default": 100},
            "random_position": {"name": "Рандомное размещение", "type": "position"}
        }
    },
    "TextLayer": {
        "name": "Текст",
        "image": "Text",
        "color": "#4A89FF0D",
        "border_color": "#4A89FF",
        "params": {
            "text": {"name": "Текст", "type": "multi_text"},
            "font": {"name": "Шрифт", "type": "file"},
            "color": {"name": "Цвет", "type": "color", "default": "#FFFFFF"},
            "align": {"name": "Позиция", "type": "align", "default": "left"},
            "size": {"name": "Размер", "type": "number", "min": 1, "max": 150, "step": 1, "default": 20},
            "stroke": {"name": "Обводка", "type": "number", "min": 1, "max": 72, "step": 1, "default": 0},
            "stroke_color": {"name": "Цвет обводки", "type": "color", "default": "#FFFFFF"},
            "border": {"name": "Рамка", "type": "number", "min": 0, "max": 50, "step": 1, "default": 0},
            "border_color": {"name": "Цвет рамки", "type": "color", "default": "#FFFFFF00"},
            "border_radius": {"name": "Закругление рамки", "type": "number", "min": 0, "max": 50, "step": 1, "default": 0},
            "random_position": {"name": "Рандомное размещение", "type": "position"}
        }
    }
}


DISPLAY_P3_ICC_B64 = (
    "AAACGGFwcGwEAAAAbW50clJHQiBYWVogB+YAAQABAAAAAAAAYWNzcEFQUEwAAAAAQVBQTAAAAAAAAAAAAAAAAAAAAAAAAPbW"
    "AAEAAAAA0y1hcHBsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKZGVzYwAAAPwAAAAw"
    "Y3BydAAAASwAAABQd3RwdAAAAXwAAAAUclhZWgAAAZAAAAAUZ1hZWgAAAaQAAAAUYlhZWgAAAbgAAAAUclRSQwAAAcwAAAAg"
    "Y2hhZAAAAewAAAAsYlRSQwAAAcwAAAAgZ1RSQwAAAcwAAAAgbWx1YwAAAAAAAAABAAAADGVuVVMAAAAUAAAAHABEAGkAcwBw"
    "AGwAYQB5ACAAUAAzbWx1YwAAAAAAAAABAAAADGVuVVMAAAA0AAAAHABDAG8AcAB5AHIAaQBnAGgAdAAgAEEAcABwAGwAZQAg"
    "AEkAbgBjAC4ALAAgADIAMAAyADJYWVogAAAAAAAA9tUAAQAAAADTLFhZWiAAAAAAAACD3wAAPb////+7WFlaIAAAAAAAAEq/"
    "AACxNwAACrlYWVogAAAAAAAAKDgAABELAADIuXBhcmEAAAAAAAMAAAACZmYAAPKnAAANWQAAE9AAAApbc2YzMgAAAAAAAQxC"
    "AAAF3v//8yYAAAeTAAD9kP//+6L///2jAAAD3AAAwG4="
)
_IPHONE_EXIF_PROFILES = [
    ("iPhone 11",        "iPhone 11 back dual wide camera 4.25mm f/1.8",    4.25,  26, 1.8,  (1.54, 4.25, 1.8, 2.4), 13),
    ("iPhone 12",        "iPhone 12 back dual wide camera 4.2mm f/1.6",     4.2,   26, 1.6,  (1.54, 4.2,  1.6, 2.4), 14),
    ("iPhone 12 Pro",    "iPhone 12 Pro back triple camera 5.1mm f/1.6",    5.1,   26, 1.6,  (1.54, 6.0,  1.6, 2.4), 14),
    ("iPhone 13",        "iPhone 13 back dual wide camera 5.1mm f/1.6",     5.1,   26, 1.6,  (1.57, 5.1,  1.6, 2.4), 15),
    ("iPhone 13 Pro",    "iPhone 13 Pro back triple camera 5.7mm f/1.5",    5.7,   26, 1.5,  (1.57, 7.7,  1.5, 2.8), 15),
    ("iPhone 14",        "iPhone 14 back dual wide camera 5.7mm f/1.5",     5.7,   26, 1.5,  (1.71, 5.7,  1.5, 2.4), 16),
    ("iPhone 14 Pro",    "iPhone 14 Pro back triple camera 6.86mm f/1.78",  6.86,  24, 1.78, (2.22, 9.0,  1.78, 2.8), 16),
    ("iPhone 15",        "iPhone 15 back dual wide camera 6.765mm f/1.6",   6.765, 26, 1.6,  (1.71, 6.765,1.6, 2.4), 17),
    ("iPhone 15 Pro",    "iPhone 15 Pro back triple camera 6.765mm f/1.78", 6.765, 24, 1.78, (2.22, 9.0,  1.78, 2.8), 17),
    ("iPhone 17 Pro Max","iPhone 17 Pro Max back triple camera 6.765mm f/1.78", 6.765, 48, 1.78, (2.22, 16.89, 1.78, 2.8), 26),
]
_VALID_IOS_MAJORS = (13, 14, 15, 16, 17, 18, 26)
_EXIF_TYPE_UNDEFINED = 7
_EXIF_TYPE_SRATIONAL = 10
_EXIF_TYPE_CORRECTIONS = {
    0x9101: _EXIF_TYPE_UNDEFINED,
    0x927c: _EXIF_TYPE_UNDEFINED,
    0xa301: _EXIF_TYPE_UNDEFINED,
    0x9201: _EXIF_TYPE_SRATIONAL,
    0x9203: _EXIF_TYPE_SRATIONAL,
    0x9204: _EXIF_TYPE_SRATIONAL,
}
_IPHONE_MAKERNOTE_TEMPLATE_B64 = (
    "QXBwbGUgaU9TAAABTU0ALgABAAkAAAABAAAAEAACAAcAAAIAAAACPAADAAcAAABoAAAEPAAEAAkAAAABAAAAAAAFAAkAAAABAAAAXAAGAAkAAAABAAAAIQAHAAkAAAABAAAAAQAIAAoAAAADAAAEpAAMAAoAAAACAAAEvAANAAkAAAABAAAAFQAOAAkAAAABAAAAAAAPAAkAAAABAAAAAgAQAAkAAAABAAAAAwAUAAkAAAABAAAABgAXABAAAAABAAAEzAAZAAkAAAABAAAAAAAaAAIAAAAGAAAE1AAcAAkAAAABAAAAAQAfAAkAAAABAAAAAAAgAAIAAAAlAAAE2gAhAAoAAAABAAAE/wAjAAkAAAACAAAFBwAlABAAAAABAAAFDwAmAAkAAAABAAAAAwAnAAoAAAABAAAFFwArAAIAAAAlAAAFHwAtAAkAAAABAAATrwAuAAkAAAABAAAAAQAvAAkAAAABAAAA9AAzAAkAAAABAAAAAAA0AAkAAAABAAAAAQA1AAkAAAABAAAAAAA2AAkAAAABAAAAAAA3AAkAAAABAAAABAA6AAkAAAABAAAAAAA7AAkAAAABAAAAAAA8AAkAAAABAAAABABBAAkAAAABAAAAAABKAAkAAAABAAAAAgBNAAoAAAABAAAFRABOAAcAAAB5AAAFTABPAAcAAAArAAAFxQBVAAkAAAABAAAAAABYAAkAAAABAAAFAwBgAAkAAAABAAALzwBhAAkAAAABAAAAGgAAAABcAHQAfwAtAB0AEAA1AFAAZAC6ABECfQIdAkYBbgAbABEAGQA7AD8ADQAKAAoAEQAhAGoAzgGVAh8C/QAeABQADgAOAA4ADQALAAsACwANAA8ALgBoAR0C7wG+ABEADgANAAsACwALAAoACgALAA0AEAAeAF0B/AHwAaQAEQAQAAoACgAJAAkACQAJAAoADQAPABYAVAFKAkkCcgARABEACgAJAAkACAAIAAkACQALAA4AEwDgAGkCKAI4ABEAEQAIAAgABwAHAAcABwAJAAoADQAQAFMAgAFXARIAEAARAAcABwAHAAYABwAHAAgACwAMAA4ADgAiAFEAEAAQABIACwAHAAcABgAGAAUABwAJAAwADAANAA0AEgAPABAAEQAJAAwACAAGAAYABgAHAAgACwAKAAsADQAQAA4AEAAOAAcACAANAAsACAAGAAYACAAKAAkACgAMAA0ADgAOAA0ACQAGAAYACwAOAAoABgAHAAkACgAJAAoADAANAA4ADQALAAkABwAHAAgADQAMAAcABwAJAAkACgALAAwADQAOAAsACQAHAAYABgAGAAsACwAHAAgACQAJAAsADAAOAA4ACgAIAAkACAAHAAYABQAHAAkACAAIAAgACgAKAAsADQAJAAkACwAJAAgABgAFAAUABgAGAAYABwAIAAoACgALAGJwbGlzdDAw1AECAwQFBgcIVWZsYWdzVXZhbHVlWXRpbWVzY2FsZVVlcG9jaBABEwAADypxAepQEjuaygAQAAgRFx0nLS84PQAAAAAAAAEBAAAAAAAAAAkAAAAAAAAAAAAAAAAAAAA///+pWQAAj5L//96LAACnpP//x5IAAElTAAAAkwAAAQAAAACRAAAAgAAAAAAAAAAAcTc1MG4ARDVEMzFERDItMDI1QS00M0QwLTg5QTEtMkM3RjdDRDhFMzA3AAAAAAAAAAABAAAACBAAAGYAAAAAAACcPAAAcVoAAGenNDM0MTBCREEtRjk4MC00MjE2LUExM0YtOTUzNjQ5MUMzODcyAAAAACAAAAABYnBsaXN0MDDSAQIDBFExUTIQA6IFCtIGBwgJUzIuMVMyLjIjQG+5gkAAAAAjQLU9AAAAAADSBgcLDCMAAAAAAAAAACNASYAAAAAAAAgNDxETFhsfIyw1OkMAAAAAAAABAQAAAAAAAAANAAAAAAAAAAAAAAAAAAAATGJwbGlzdDAwEAAIAAAAAAAAAQEAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAo="
)
_MN_IDENTIFIER_FIELDS = (1242, 37), (1311, 37)
_MN_ACCEL_OFFSET = 1188
_MN_INLINE_JITTER_OFFSETS = (
    60,
    72,
    84,
    96,
    336,
    360,
    540, 552, 564,
)
_MN_RUNTIME_VALUE_OFFSET = 1132
_MN_SNR_OFFSET = 1303


def _rational(value, denom=1000):
    return IFDRational(int(round(value * denom)), denom)


def _random_apple_makernote() -> bytes:
    mn = bytearray(base64.b64decode(_IPHONE_MAKERNOTE_TEMPLATE_B64))

    for offset, length in _MN_IDENTIFIER_FIELDS:
        new_uuid = (str(uuid.uuid4()).upper() + "\x00").encode("ascii")
        mn[offset:offset + length] = new_uuid[:length].ljust(length, b"\x00")

    vx, vy, vz = (random.uniform(-1, 1) for _ in range(3))
    norm = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
    vx, vy, vz = vx / norm, vy / norm, vz / norm
    packed = b""
    for v in (vx, vy, vz):
        denom = random.randint(15000, 50000)
        numer = int(round(v * denom))
        packed += struct.pack(">ii", numer, denom)
    mn[_MN_ACCEL_OFFSET:_MN_ACCEL_OFFSET + 24] = packed

    for off in _MN_INLINE_JITTER_OFFSETS:
        (orig,) = struct.unpack(">i", bytes(mn[off:off + 4]))
        jittered = max(0, int(round(orig * random.uniform(0.7, 1.3))) + random.randint(-3, 3))
        mn[off:off + 4] = struct.pack(">i", jittered)

    new_runtime_ns = random.randint(3_600 * 10**9, 10 * 86_400 * 10**9)
    mn[_MN_RUNTIME_VALUE_OFFSET:_MN_RUNTIME_VALUE_OFFSET + 8] = new_runtime_ns.to_bytes(8, "big")

    (snr_num, snr_den) = struct.unpack(">ii", bytes(mn[_MN_SNR_OFFSET:_MN_SNR_OFFSET + 8]))
    snr_val = max(0.1, (snr_num / snr_den) * random.uniform(0.7, 1.3))
    mn[_MN_SNR_OFFSET:_MN_SNR_OFFSET + 8] = struct.pack(">ii", int(round(snr_val * 100000)), 100000)

    return bytes(mn)


_GPS_LAND_REGIONS = [
    (43.15, 43.30, 76.85, 77.05),
    (51.08, 51.18, 71.38, 71.48),
    (55.65, 55.80, 37.40, 37.70),
    (50.40, 50.48, 30.45, 30.58),
    (52.18, 52.28, 20.95, 21.05),
    (52.47, 52.53, 13.35, 13.45),
    (48.82, 48.88, 2.28, 2.38),
    (41.00, 41.08, 28.92, 29.08),
    (41.27, 41.33, 69.24, 69.32),
    (51.47, 51.53, -0.13, -0.03),
    (40.68, 40.78, -74.02, -73.92),
    (34.02, 34.08, -118.32, -118.22),
]


def _random_land_point():
    lat_min, lat_max, lon_min, lon_max = random.choice(_GPS_LAND_REGIONS)
    return random.uniform(lat_min, lat_max), random.uniform(lon_min, lon_max)


def _dms(value):
    deg = int(abs(value))
    min_f = (abs(value) - deg) * 60
    minute = int(min_f)
    sec = (min_f - minute) * 60
    return [IFDRational(deg, 1), IFDRational(minute, 1), IFDRational(int(round(sec * 100)), 100)]


def _fix_exif_tag_types(exif_bytes: bytes) -> bytes:
    data = bytearray(exif_bytes)
    prefix_len = 6 if bytes(data[:6]) == b"Exif\x00\x00" else 0
    bo = ">" if data[prefix_len:prefix_len + 2] == b"MM" else "<"

    def u16(off):
        return struct.unpack(bo + "H", data[off:off + 2])[0]

    def u32(off):
        return struct.unpack(bo + "I", data[off:off + 4])[0]

    def walk_ifd(ifd_offset_within_tiff, depth=0):
        if depth > 8:
            return
        abs_off = prefix_len + ifd_offset_within_tiff
        count = u16(abs_off)
        entry_base = abs_off + 2
        for i in range(count):
            eoff = entry_base + i * 12
            tag = u16(eoff)
            typ = u16(eoff + 2)
            wanted = _EXIF_TYPE_CORRECTIONS.get(tag)
            if wanted is not None and typ != wanted:
                data[eoff + 2:eoff + 4] = struct.pack(bo + "H", wanted)
            if tag in (0x8769, 0x8825):
                walk_ifd(u32(eoff + 8), depth + 1)
        next_ifd = u32(entry_base + count * 12)
        if next_ifd:
            walk_ifd(next_ifd, depth + 1)

    try:
        walk_ifd(u32(prefix_len + 4))
    except (struct.error, IndexError):
        return exif_bytes

    return bytes(data)


def random_exif_bytes(width=0, height=0, add_gps=False):
    model, lens_model, focal_mm, focal35, fnumber, lens_spec, min_ios_major = random.choice(_IPHONE_EXIF_PROFILES)
    dt = datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 96), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
    dt_str = dt.strftime('%Y:%m:%d %H:%M:%S')
    subsec = f"{random.randint(0, 999):03d}"

    candidates = sorted((m for m in _VALID_IOS_MAJORS if m >= min_ios_major), reverse=True)
    weights = [0.5 ** i for i in range(len(candidates))]
    ios_major = random.choices(candidates, weights=weights)[0]

    ios_ver = f"{ios_major}.{random.randint(0, 6)}"
    if random.random() < 0.5:
        ios_ver += f".{random.randint(0, 3)}"

    exposure_time = 1 / random.choice([60, 100, 120, 240, 480, 1000, 2000])
    iso = random.choice([25, 32, 40, 50, 64, 80, 100, 125, 160, 200, 250, 320])
    exposure_bias = random.uniform(-0.5, 0.5)

    orientation = 1

    exif = Image.Exif()
    exif[271] = "Apple"
    exif[272] = model
    exif[305] = ios_ver
    exif[306] = dt_str
    exif[274] = orientation
    exif[282] = IFDRational(72, 1)
    exif[283] = IFDRational(72, 1)
    exif[296] = 2
    exif[531] = 1

    try:
        exif_ifd = exif.get_ifd(0x8769)
        exif_ifd[36864] = b"0232"
        exif_ifd[37121] = b"\x01\x02\x03\x00"
        exif_ifd[36867] = dt_str
        exif_ifd[36868] = dt_str
        exif_ifd[37521] = subsec
        exif_ifd[37522] = subsec
        exif_ifd[33434] = _rational(exposure_time, 1000000)
        exif_ifd[33437] = _rational(fnumber, 10)
        exif_ifd[34850] = 2
        exif_ifd[34855] = iso
        exif_ifd[37377] = _rational(-math.log2(exposure_time), 1000)
        exif_ifd[37378] = _rational(2 * math.log2(fnumber), 1000)
        exif_ifd[37379] = _rational(random.uniform(1.5, 9.5), 1000)
        exif_ifd[37380] = _rational(exposure_bias, 1000)
        exif_ifd[37383] = random.choice([3, 5])
        exif_ifd[37385] = random.choice([16, 24])
        exif_ifd[37386] = _rational(focal_mm, 100)

        if width and height:
            exif_ifd[40962] = width
            exif_ifd[40963] = height
            area_w = max(1, int(width * random.uniform(0.09, 0.16)))
            area_h = max(1, int(height * random.uniform(0.10, 0.18)))
            cx = int(width * random.uniform(0.42, 0.58))
            cy = int(height * random.uniform(0.38, 0.55))
            cx = min(max(cx, area_w // 2), width - area_w // 2 - 1) if width > area_w else width // 2
            cy = min(max(cy, area_h // 2), height - area_h // 2 - 1) if height > area_h else height // 2
            exif_ifd[37396] = (cx, cy, area_w, area_h)
        exif_ifd[41495] = 2
        exif_ifd[41729] = b"\x01"
        exif_ifd[40960] = b"0100"
        exif_ifd[40961] = 1
        exif_ifd[41986] = 0
        exif_ifd[41987] = 0
        exif_ifd[41989] = focal35
        exif_ifd[41990] = 0
        exif_ifd[42034] = [_rational(v, 1000) for v in lens_spec]
        exif_ifd[42035] = "Apple"
        exif_ifd[42036] = lens_model
        try:
            exif_ifd[37500] = _random_apple_makernote()
        except Exception:
            pass
    except Exception:
        pass

    if add_gps:
        try:
            gps_ifd = exif.get_ifd(0x8825)
            lat, lon = _random_land_point()
            utc = dt + datetime.timedelta(hours=random.randint(-3, 3))
            gps_ifd[1] = "N" if lat >= 0 else "S"
            gps_ifd[2] = _dms(lat)
            gps_ifd[3] = "E" if lon >= 0 else "W"
            gps_ifd[4] = _dms(lon)
            gps_ifd[5] = 0
            gps_ifd[6] = _rational(random.uniform(0, 300), 100)
            gps_ifd[7] = [IFDRational(utc.hour, 1), IFDRational(utc.minute, 1), IFDRational(utc.second, 1)]
            gps_ifd[12] = "K"
            gps_ifd[13] = IFDRational(0, 1)
            gps_ifd[16] = "T"
            gps_ifd[17] = _rational(random.uniform(0, 360), 10)
            gps_ifd[29] = dt.strftime('%Y:%m:%d')
        except Exception:
            pass

    raw = exif.tobytes()
    try:
        return _fix_exif_tag_types(raw)
    except Exception:
        return raw


def generate_formatted_string(original_string: str, additional_args: dict = {"username": "@john_doe"}) -> str:
    current_date = datetime.datetime.now()

    days = {
        "Monday": ["Monday", "Понедельник"],
        "Tuesday": ["Tuesday", "Вторник"],
        "Wednesday": ["Wednesday", "Среда"],
        "Thursday": ["Thursday", "Четверг"],
        "Friday": ["Friday", "Пятница"],
        "Saturday": ["Saturday", "Суббота"],
        "Sunday": ["Sunday", "Воскресенье"],
    }
    emojis = {
        "Smilies & Emotion": ["😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "😗", "😙", "😚", "🙂", "🤗", "🤔"],
        "People & Body": ["👶", "👧", "👦", "👩", "👨", "👩‍🦰", "👨‍🦱", "👩‍🦳", "👨‍🦳", "👩‍🦲", "👨‍🦲", "👩‍🦱", "👨‍🦱", "👩‍🦰", "👨‍🦰", "👩‍🦳", "👨‍🦳", "👩‍🦲", "👨‍🦲", "👩‍🦱"],
        "Animals & Nature": ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐽", "🐸", "🐵", "🙈", "🙉", "🙊", "🐒"],
        "Food & Drink": ["🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🍅", "🍆", "🥑", "🥦", "🥒", "🥬"],
        "Activities": ["⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🎱", "🏓", "🏸", "🥊", "🥋", "🥅", "⛳", "⛸️", "🎣", "🎿", "🛷", "🥌"],
        "Travel & Places": ["🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐", "🚚", "🚛", "🚜", "🏍️", "🛵", "🚲", "🛴", "🚏", "🛣️", "🛤️"],
        "Objects": ["💡", "🔦", "🕯️", "💸", "💵", "💴", "💶", "💷", "💰", "💳", "💎", "⚖️", "🔧", "🔨", "🔩", "🔧", "🔨", "🔩", "🗜️", "⚙️"],
        "Symbols": ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "💔", "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "☮️", "✝️", "☪️"],
        "Flags": ["🇺🇸", "🇨🇦", "🇬🇧", "🇦🇺", "🇫🇷", "🇩🇪", "🇮🇹", "🇪🇸", "🇯🇵", "🇨🇳", "🇷🇺", "🇧🇷", "🇮🇳", "🇲🇽", "🇿🇦"]
    }
    emojis["all"] = emojis["Smilies & Emotion"] + emojis["People & Body"] + emojis["Animals & Nature"] + emojis["Food & Drink"] + emojis["Activities"] + emojis["Travel & Places"] + emojis["Objects"] + emojis["Symbols"] + emojis["Flags"]

    original_string = original_string.replace("{today}", days[current_date.strftime("%A")][0])
    original_string = original_string.replace("{dd}", current_date.strftime("%d"))
    original_string = original_string.replace("{mm}", current_date.strftime("%m"))
    original_string = original_string.replace("{yyyy}", current_date.strftime("%Y"))
    original_string = original_string.replace("{yy}", current_date.strftime("%y"))
    if additional_args.get("username", "@") is not None:
        original_string = original_string.replace("{username}", additional_args.get("username", "@").replace("@", "", 1))
        original_string = original_string.replace("{@username}", additional_args.get("username", "@"))
    original_string = original_string.replace("{hour}", current_date.strftime("%H"))
    original_string = original_string.replace("{min}", current_date.strftime("%M"))
    original_string = original_string.replace("{sec}", current_date.strftime("%S"))
    original_string = original_string.replace("{emoji}", random.choice(emojis["all"]))
    original_string = original_string.replace("{emoji_face}", random.choice(emojis["Smilies & Emotion"]))
    original_string = original_string.replace("{emoji_people}", random.choice(emojis["People & Body"]))
    original_string = original_string.replace("{emoji_animal}", random.choice(emojis["Animals & Nature"]))
    original_string = original_string.replace("{emoji_food}", random.choice(emojis["Food & Drink"]))
    original_string = original_string.replace("{emoji_activities}", random.choice(emojis["Activities"]))
    original_string = original_string.replace("{emoji_car}", random.choice(emojis["Travel & Places"]))
    original_string = original_string.replace("{emoji_objects}", random.choice(emojis["Objects"]))
    original_string = original_string.replace("{emoji_symbols}", random.choice(emojis["Symbols"]))
    original_string = original_string.replace("{emoji_flags}", random.choice(emojis["Flags"]))

    def replace_numbers(input_string):
        def replace_match(match):
            range_str = match.group(1)
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                if start > end:
                    return "{" + str(start) + "-" + str(end) + "}"
                return str(random.randint(start, end))
            else:
                number = int(range_str)
                return str(random.randint(0, number))

        return re.sub(r'\{(\d+-\d+|\d+)\}', replace_match, input_string)

    def replace_file_once(input_string):
        def replace_match(key, once):
            filePath = configs.ROOT_PATH / f"{key}.txt"

            if not filePath.exists():
                return ""

            with filePath.open("r", encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                return ""

            chosen = random.choice(lines).strip()

            if once:
                lines = [line for line in lines if line.strip() != chosen]
                with filePath.open("w", encoding="utf-8") as f:
                    f.writelines(lines)

            return chosen

        input_string = re.sub(r"\{file_once-([^}]+)\}", lambda m: replace_match(m.group(1), once=True), input_string)
        input_string = re.sub(r"\{file-([^}]+)\}", lambda m: replace_match(m.group(1), once=False), input_string)
        return input_string

    def replace_file(input_string):
        def replace_match(match):
            range_str = match.group(1)
            filePath = configs.ROOT_PATH / f"{range_str}.txt"
            if filePath.exists():
                all_lines = []
                with filePath.open("r", encoding="utf-8") as f:
                    all_lines = f.readlines()

                if len(all_lines) > 0:
                    return random.choice(all_lines).replace("\r", "").replace("\n", "")

        return re.sub(r"\{file-([^}]+)\}", replace_match, input_string)

    original_string = replace_numbers(original_string)
    original_string = replace_file(original_string)
    original_string = replace_file_once(original_string)
    original_string = original_string.replace("\\n", "\n")

    all_tags = []
    tagsFilePath = configs.ROOT_PATH / "tags.txt"
    if tagsFilePath.exists():
        with tagsFilePath.open("r", encoding="utf-8") as f:
            all_tags = f.readlines()

    for _ in range(original_string.count("{tag}")):
        if len(all_tags) > 0:
            selected_tag = random.choice(all_tags)
            original_string = original_string.replace("{tag}", selected_tag.replace("\r", "").replace("\n", ""), 1)
            all_tags.remove(selected_tag)

    pattern = re.compile(r"\{([^{}]+)\}")
    while True:
        match = pattern.search(original_string)
        if not match:
            break
        options = match.group(1).split("|")
        replacement = random.choice(options)
        original_string = original_string[:match.start()] + replacement + original_string[match.end():]

    return original_string


class BasePhotoLayer:

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.settings = settings

        if all(k in self.settings for k in ("random_position_x", "random_position_y", "random_position_width", "random_position_height")):
            rect_x = int(self.settings["random_position_x"])
            rect_y = int(self.settings["random_position_y"])
            rect_w = int(self.settings["random_position_width"])
            rect_h = int(self.settings["random_position_height"])

            max_x = rect_x + rect_w - width
            max_y = rect_y + rect_h - height

            self.x = random.randint(rect_x, max_x) if max_x > rect_x else rect_x
            self.y = random.randint(rect_y, max_y) if max_y > rect_y else rect_y

    async def process(self, canvas: Image.Image) -> Image.Image: pass

    def parse_color(self, value: str) -> tuple[int, int, int, int]:

        value = value.strip().lstrip("#")

        if len(value) == 3:
            r = int(value[0] * 2, 16)
            g = int(value[1] * 2, 16)
            b = int(value[2] * 2, 16)
            return r, g, b, 255

        if len(value) == 4:
            r = int(value[0] * 2, 16)
            g = int(value[1] * 2, 16)
            b = int(value[2] * 2, 16)
            a = int(value[3] * 2, 16)
            return r, g, b, a

        if len(value) == 6:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
            return r, g, b, 255

        if len(value) == 8:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
            a = int(value[6:8], 16)
            return r, g, b, a

        return 255, 255, 255, 255


class SnowLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:

        def _draw():

            snow_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            snow_draw = ImageDraw.Draw(snow_layer)

            for _ in range(int(self.settings.get("snow_count", 1))):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height)
                r = self.settings.get("snow_size", 1)
                snow_draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(255 * random.uniform(0, 1))))

            del snow_draw
            canvas.paste(snow_layer, (self.x, self.y), mask=snow_layer)

        await asyncio.to_thread(_draw)

        return canvas


class LinesLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:

        def _draw():

            draw = ImageDraw.Draw(canvas)

            line_width = self.settings.get("line_width", 1)
            line_thickness = self.settings.get("line_thickness", 1)

            for y in np.arange(0, 1, 0.01):
                for x in np.arange(random.uniform(0, 0.3), 1, random.uniform(0.1, 0.3)):
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                    draw.line((int(x * self.width) + self.x, int(y * self.height) + self.y, int(x * self.width + int(line_width)) + self.x, int(y * self.height + int(line_width)) + self.y), fill=color, width=int(line_thickness))

            del draw

        await asyncio.to_thread(_draw)

        return canvas


class BlurLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:

        def _draw():

            intensity = self.settings.get("intensity", 1)
            feather = self.settings.get("feather", 30)

            crop = canvas.crop((self.x, self.y, self.x + self.width, self.y + self.height))
            blurred = crop.filter(ImageFilter.GaussianBlur(intensity))

            mask = Image.new("L", (self.width, self.height), 0)
            draw = ImageDraw.Draw(mask)

            inset = feather * 2
            draw.rectangle((inset, inset, self.width - inset, self.height - inset), fill=255)

            mask = mask.filter(ImageFilter.GaussianBlur(feather))

            canvas.paste(blurred, (self.x, self.y), mask)


        await asyncio.to_thread(_draw)
        return canvas


class EmojiLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:

        def _draw(image_bytes):
            emoji_scale_factor = self.settings.get("emoji_scale_factor", 1)
            emoji_opacity = self.settings.get("emoji_opacity", 100) / 100
            emoji_count = self.settings.get("emoji_count", 1)

            emoji_image = Image.open(image_bytes)
            emoji_image = emoji_image.resize((int(32 * emoji_scale_factor), int(32 * emoji_scale_factor)))

            emoji_data = emoji_image.getdata()
            emoji_new_data = []
            for item in emoji_data:
                emoji_new_data.append((item[0], item[1], item[2], int(item[3] * emoji_opacity)))
            emoji_image.putdata(emoji_new_data)

            for i in range(int(emoji_count)):
                canvas.paste(emoji_image, (random.randint(self.x, self.x + self.width), random.randint(self.y, self.y + self.height)), mask=emoji_image.split()[-1])

        try:
            async with curl_cffi.AsyncSession() as session:
                await asyncio.to_thread(_draw, io.BytesIO((await session.get("https://api2.snaipix.com/unique/get_random_emoji")).content))
        except: pass

        return canvas


class TextLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        if "text" in settings:
            settings["text"] = generate_formatted_string(settings["text"], {})

        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:

        def _draw():
            dummy = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy)

            try:
                font = ImageFont.truetype(self.settings.get("font", "arial.ttf"), self.settings.get("size", 20))
            except:
                return

            stroke = self.settings.get("stroke", 0)
            text = self.settings.get("text", "")
            align = self.settings.get("align", "left")

            bbox = draw.multiline_textbbox((0, 0), text, font=font, align=align, stroke_width=stroke)
            text_w = int(bbox[2] - bbox[0])
            text_h = int(bbox[3] - bbox[1])

            dummy.close()
            del dummy

            border = int(self.settings.get("border", 0))
            border_radius = int(self.settings.get("border_radius", 0))
            border_color = self.parse_color(self.settings.get("border_color", "#FFFFFF00"))

            tmp_w = text_w + border * 2
            tmp_h = text_h + border * 2

            tmp = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tmp)

            if border > 0:
                draw.rounded_rectangle(
                    (0, 0, tmp_w - 1, tmp_h - 1),
                    radius=border_radius,
                    fill=border_color
                )

            draw.multiline_text(
                (border - bbox[0], border - bbox[1]),
                text,
                fill=self.parse_color(self.settings.get("color", "#FFFFFF")),
                font=font,
                align=align,
                stroke_width=stroke,
                stroke_fill=self.parse_color(self.settings.get("stroke_color", "#FFFFFF"))
            )

            x, y = self.x, self.y

            if align == "center":
                x = self.x + (self.width - tmp_w) // 2
            if align == "right":
                x = self.x + self.width - tmp_w

            y = self.y + (self.height - tmp_h) // 2

            bbox = tmp.getbbox()
            if not bbox:
                tmp.close()
                return

            tmp = tmp.crop(bbox)

            if self.settings.get("rotate", False):
                tmp = tmp.rotate(
                    random.randint(self.settings.get("rotate_min", 0), self.settings.get("rotate_max", 10)),
                    expand=True
                )

            canvas.paste(tmp, (int(x), int(y)), tmp)

            tmp.close()
            del tmp

        await asyncio.to_thread(_draw)

        return canvas


class PhotoLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:

        if self.settings.get("method", "Фоны софта") == "Фоны софта":
            async with curl_cffi.AsyncSession() as session:
                photo = await asyncio.to_thread(Image.open, io.BytesIO((await session.get("https://api2.snaipix.com/unique/get_random_image")).content))
        elif self.settings.get("method", "Фоны софта") == "Генерировать":
            photo = Image.new("RGBA", (self.width, self.height))
            draw = ImageDraw.Draw(photo)

            draw.rectangle((0, 0, self.width, self.height), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255))

            for _ in range(random.randint(10, 20)):
                x = int(self.width * random.uniform(0, 1))
                y = int(self.height * random.uniform(0, 1))
                w = 100 * random.uniform(0.1, 10)
                h = 100 * random.uniform(0.1, 10)
                start_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                end_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)

                for i in range(int(w)):
                    r = int(start_color[0] * (1 - i / w) + end_color[0] * (i / w))
                    g = int(start_color[1] * (1 - i / w) + end_color[1] * (i / w))
                    b = int(start_color[2] * (1 - i / w) + end_color[2] * (i / w))
                    col = (r, g, b, 255)

                    draw.line([(x + i, y), (x + i, y + h)], fill=col)

            for _ in range(random.randint(10, 20)):
                x = int(self.width * random.uniform(0, 1))
                y = int(self.height * random.uniform(0, 1))
                w = 100 * random.uniform(0.1, 3)
                h = 100 * random.uniform(0.1, 3)
                col = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                draw.ellipse((x, y, x + w, y + h), fill=col)

            del draw
        elif self.settings.get("method", "Фоны софта") == "Генерировать (ИИ)":
            pass
        else:
            if not self.settings.get("source"): return canvas

            if os.path.isdir(self.settings.get("source")):
                files = await asyncio.to_thread(os.listdir, self.settings.get("source"))
                if not files: return canvas

                files = [v for v in files if v.endswith((".jpg", ".png"))]

                file = await asyncio.to_thread(os.path.join, self.settings.get("source"), random.choice(files))
                if not file: return canvas

                photo = await asyncio.to_thread(Image.open, file)
                if not photo: return canvas
            else:
                photo = await asyncio.to_thread(Image.open, self.settings.get("source"))
                if not photo: return canvas

        try:
            photo = await asyncio.to_thread(photo.convert, "RGBA")
            photo = await asyncio.to_thread(photo.resize, (self.width, self.height))

            if self.settings.get("chromakey", False):
                key = self.parse_color(self.settings.get("chromakey_color", "#00FF00"))
                tolerance = self.settings.get("chromakey_tolerance", 60)

                pixels = photo.load()

                for py in range(photo.height):
                    for px in range(photo.width):
                        r, g, b, a = pixels[px, py]

                        if (
                            abs(r - key[0]) <= tolerance and
                            abs(g - key[1]) <= tolerance and
                            abs(b - key[2]) <= tolerance
                        ):
                            pixels[px, py] = (r, g, b, 0)

            alpha = self.settings.get("opacity", 100) / 100
            if alpha < 1:
                r, g, b, a = await asyncio.to_thread(photo.split)
                a = await asyncio.to_thread(a.point, lambda p: int(p * alpha))
                photo = await asyncio.to_thread(Image.merge, "RGBA", (r, g, b, a))

            rounded = self.settings.get("round", 0)
            if rounded > 0:
                mask = Image.new("L", (self.width, self.height), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle((0, 0, self.width, self.height), radius=rounded, fill=255)
                photo.putalpha(ImageChops.multiply(photo.getchannel("A"), mask))

            border = self.settings.get("border", 0)
            border_color = self.parse_color(self.settings.get("border_color", "#FFFFFF"))
            paste_x = self.x
            paste_y = self.y

            if border > 0:
                new_w = self.width + border * 2
                new_h = self.height + border * 2

                bordered = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
                border_draw = ImageDraw.Draw(bordered)

                border_draw.rounded_rectangle(
                    (0, 0, new_w - 1, new_h - 1),
                    radius=rounded + border,
                    fill=border_color
                )

                inner_mask = Image.new("L", (self.width, self.height), 0)
                inner_draw = ImageDraw.Draw(inner_mask)
                inner_draw.rounded_rectangle(
                    (0, 0, self.width - 1, self.height - 1),
                    radius=rounded,
                    fill=255
                )

                bordered.paste(photo, (border, border), photo)

                photo.close()
                photo = bordered

                paste_x = self.x - border
                paste_y = self.y - border

            if self.settings.get("rotate", False):
                rotate_value = random.randint(self.settings.get("rotate_min", 0), self.settings.get("rotate_max", 10))
                photo = await asyncio.to_thread(photo.rotate, rotate_value, expand=True)

            await asyncio.to_thread(canvas.paste, photo, (paste_x, paste_y), photo if photo.mode == "RGBA" else None)
        finally:
            await asyncio.to_thread(photo.close)
            del photo

        return canvas


class NoiseLayer(BasePhotoLayer):

    def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float, settings: dict):
        BasePhotoLayer.__init__(self, x, y, width, height, settings)

    async def process(self, canvas: Image.Image) -> Image.Image:
        def _draw():
            try:
                image = canvas.convert("RGBA")
                layer = image.crop((self.x, self.y, self.x + self.width, self.y + self.height))

                image_array = np.array(layer).astype(np.int16)

                noise = np.random.normal(
                    loc=0,
                    scale=255 * (self.settings.get("noise_intensity", 0) / 100),
                    size=image_array.shape
                ).astype(np.int16)
                noise[:, :, 3] = 0
                noisy_array = image_array + noise
                noisy_array = np.clip(noisy_array, 0, 255).astype(np.uint8)

                noisy_layer = Image.fromarray(noisy_array, "RGBA")
                image.paste(noisy_layer, (self.x, self.y), noisy_layer)
            except:
                return canvas
            finally:
                del image_array, noise, noisy_array

            return image

        return await asyncio.to_thread(_draw)


async def layered_photo_unique(canvas_settings: dict, layers: list[BasePhotoLayer]) -> Image.Image:

    canvas: Image.Image = await asyncio.to_thread(Image.new, "RGB", (canvas_settings["width"], canvas_settings["height"]), (255, 255, 255))

    for layer in layers:
        canvas = await layer.process(canvas)

    return canvas


async def get_preview(layers: list) -> Image.Image:

    python_layers = []
    for layer in layers:
        python_obj = BasePhotoLayer
        if layer.get("layer") == "PhotoLayer": python_obj = PhotoLayer
        elif layer.get("layer") == "TextLayer": python_obj = TextLayer
        elif layer.get("layer") == "NoiseLayer": python_obj = NoiseLayer
        elif layer.get("layer") == "SnowLayer": python_obj = SnowLayer
        elif layer.get("layer") == "LinesLayer": python_obj = LinesLayer
        elif layer.get("layer") == "EmojiLayer": python_obj = EmojiLayer
        elif layer.get("layer") == "BlurLayer": python_obj = BlurLayer

        python_layers.append(python_obj(int(layer.get("x")), int(layer.get("y")), int(layer.get("width")), int(layer.get("height")), layer.get("settings", {})))

    return await layered_photo_unique({"width": 1080, "height": 1920}, python_layers)


def sync_get_preview(layers: list) -> bytes:
    img = asyncio.run(get_preview(layers))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70, optimize=True, progressive=True, subsampling=0)
    return buf.getvalue()


def get_video_size(video_path, is_9_16 = False):
    probe = ffmpeg.probe(video_path, FFPROBE_PATH)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    duration = 5
    try:
        fps = eval(video_stream['avg_frame_rate'])
    except Exception:
        fps = 25

    if "tags" in video_stream and "DURATION" in video_stream["tags"]:
        duration = int(video_stream["tags"]["DURATION"].split(":")[2].split(".")[0])
    if "duration" in video_stream:
        try:
            duration = float(video_stream["duration"])
        except Exception:
            duration = int(video_stream["duration"].split(".")[0])

    if is_9_16:
        return 1080, 1920, duration, fps
    else:
        return width, height, duration, fps


def split_number(n: int, segments: int):
    step = n // segments
    intervals = [(i * step, (i + 1) * step) for i in range(segments)]
    intervals[-1] = (intervals[-1][0], n)
    return intervals


def get_audio_info(audio_path: str):
    probe = ffmpeg.probe(audio_path, FFPROBE_PATH)

    audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)

    return audio_stream


def probe_video(file_path: str):
    try:
        probe = ffmpeg.probe(file_path, FFPROBE_PATH)
    except Error as e:
        print(e.stderr)
        print(e.stdout)


    video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
    audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)

    return video_stream, audio_stream


def photo_to_slideshow(files: list, dist_path: str):

    files_path = []

    for file in files:
        if isinstance(file, str):
            files_path.append(file)
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp_path = tmp.name

            with open(tmp_path, "wb") as f:
                f.write(file)

            files_path.append(tmp_path)

    files_path = list(reversed(files_path))

    n = len(files_path)
    segment = 10 / n
    inputs = []
    for path in files_path:
        inp = ffmpeg.input(path, loop=1, t=segment+1, framerate=30)
        inp = inp.filter("scale", 1080, 1920, force_original_aspect_ratio="decrease").filter("pad", 1080, 1920, "(ow-iw)/2", "(oh-ih)/2")
        inputs.append(inp)

    stream = inputs[0]
    for i in range(1, n):
        offset = segment * i - 1
        stream = ffmpeg.filter([stream, inputs[i]], "xfade", transition="slideleft", duration=1, offset=offset)

    out = ffmpeg.output(stream, dist_path, vcodec="libx264", pix_fmt="yuv420p", r=30)
    ffmpeg.run(out, cmd=FFMPEG_PATH, overwrite_output=True)

    for file in files_path:
        os.remove(file)

    return dist_path


async def video_unique_new(video_path : str, dist_path : str, selected_config: dict, render_index: int, ai_image: bytes | None = None):
    if selected_config.get("render_on_separate_server", False):
        data = {"video_path": video_path, "dist_path": dist_path, "selected_config": selected_config, "render_index": render_index}

        def recursive_file_handler(obj):
            if isinstance(obj, dict):
                for k, v in list(obj.items()):
                    if isinstance(v, str) and (os.path.isfile(v) or os.path.isdir(v)):
                        try:
                            if os.path.isfile(v):
                                obj[k] = {
                                    "file_extension": v.split(".")[-1],
                                    "file_content": base64.b64encode(open(v, "rb").read()).decode()
                                }
                            else:
                                random_file = os.path.join(v, random.choice(os.listdir(v)))
                                obj[k] = {
                                    "file_extension": random_file.split(".")[-1],
                                    "file_content": base64.b64encode(open(random_file, "rb").read()).decode()
                                }
                        except Exception:
                            pass
                    else:
                        recursive_file_handler(v)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    if isinstance(v, str) and (os.path.isfile(v) or os.path.isdir(v)):
                        try:
                            if os.path.isfile(v):
                                obj[i] = {
                                    "file_extension": v.split(".")[-1],
                                    "file_content": base64.b64encode(open(v, "rb").read()).decode()
                                }
                            else:
                                random_file = os.path.join(v, random.choice(os.listdir(v)))
                                obj[i] = {
                                    "file_extension": random_file.split(".")[-1],
                                    "file_content": base64.b64encode(open(random_file, "rb").read()).decode()
                                }
                        except Exception:
                            pass
                    else:
                        recursive_file_handler(v)

        recursive_file_handler(data)

        async with curl_cffi.AsyncSession() as session:
            file_id = (await session.post(f"http://{selected_config.get('server_ip', '127.0.0.1')}:9999/render", json=data)).json()["data"]

            while True:
                try:
                    status = (await session.get(f"http://{selected_config.get('server_ip', '127.0.0.1')}:9999/unique_status/{file_id}")).json()["data"]
                    if status == "ok":
                        break
                    elif status == "failed":
                        raise Exception("Failed to render")
                    else:
                        await asyncio.sleep(1)
                except Exception:
                    await asyncio.sleep(1)

            with open(dist_path, "wb") as f:
                f.write((await session.get(f"http://{selected_config.get('server_ip', '127.0.0.1')}:9999/get_unique/{file_id}")).content)

            await session.get(f"http://{selected_config.get('server_ip', '127.0.0.1')}:9999/delete_temp_file/{file_id}")

        return dist_path


    tempFolder = TEMP_PATH
    tempFolder.mkdir(parents=True, exist_ok=True)

    VCODECS = {
        "libx264": "H.264",
        "libx265": "H.265",
        "libaom-av1": "AV1",
        "libsvtav1": "AV1 (Fast)",
        "h264_nvenc": "H.264 (NVIDIA)",
        "hevc_nvenc": "H.265 (NVIDIA)",
        "av1_nvenc": "AV1 (NVIDIA)",
        "h264_qsv": "H.264 (Intel)",
        "hevc_qsv": "H.265 (Intel)",
        "av1_qsv": "AV1 (Intel)",
        "h264_amf": "H.264 (AMD)",
        "hevc_amf": "H.265 (AMD)",
        "av1_amf": "AV1 (AMD)",
    }
    video_encoder = "libx264"
    for k, v in VCODECS.items():
        if v == selected_config.get("codec", "H.264"):
            video_encoder = k
            break

    input_args = {}
    if "nvenc" in video_encoder: input_args["hwaccel"] = "cuda"
    elif "amf" in video_encoder: input_args["hwaccel"] = "d3d11va"

    tmp_file = ""

    width, height, duration, fps = get_video_size(video_path, selected_config.get("is_9_16", False))
    background_width = int(width)
    background_height = int(height)
    if selected_config.get("apply_background", False):
        if selected_config.get("video_position", "По центру") != "По центру" and ".mp4" in tmp_file:
            bg_width, bg_height, bg_duration, bg_fps = get_video_size(tempFolder / tmp_file)
            background_width = int(width + bg_width)
            background_height = int(height + bg_height)
        elif selected_config.get("video_position", "По центру") != "По центру" and ".png" in tmp_file:
            bg_width, bg_height = Image.open(tempFolder / tmp_file).size
            background_width = int(width + bg_width*2)
            background_height = int(height + bg_height*2)
        else:
            background_width = int(width + selected_config.get("background_size_left", 0) + selected_config.get("background_size_right", 0))
            background_height = int(height + selected_config.get("background_size_top", 0) + selected_config.get("background_size_bottom", 0))

    if selected_config.get("particle", False):
        tmp_particle_file = "".join(random.choices(string.ascii_uppercase + string.digits, k=16)) + ".png"
        particle = Image.new("RGBA", (selected_config.get("particle_size", 50)*2, selected_config.get("particle_size", 50)*2), "#00000000")

        draw = ImageDraw.Draw(particle)
        max_radius = selected_config.get("particle_size", 50)
        circle_center = (selected_config.get("particle_size", 50), selected_config.get("particle_size", 50))
        for r in range(max_radius, 0, -1):
            alpha = int(255 * ((max_radius - r) / max_radius))
            draw.ellipse((circle_center[0] - r, circle_center[1] - r, circle_center[0] + r, circle_center[1] + r), fill=(255, 255, 255, alpha))

        particle.save(tempFolder / tmp_particle_file)

    if selected_config.get("apply_background", False):
        bg = None
        tmp_file = "".join(random.choices(string.ascii_uppercase + string.digits, k=16)) + ".png"

        if bg is None and len(selected_config.get("bg_images_folder", "").strip()) > 0 and os.path.exists(selected_config.get("bg_images_folder", "")):
            if os.path.isfile(selected_config.get("bg_images_folder", "")):
                random_image = selected_config.get("bg_images_folder", "")

                if random_image.split(".")[-1].lower() in ["mp4", "webm", "mov", "avi"]:
                    bg = random_image
                else:
                    bg = Image.open(random_image).copy()
                    if selected_config.get("remove_used_bg", False):
                        _safe_unlink(random_image)
            else:
                image_files = [file for file in os.listdir(selected_config.get("bg_images_folder", "")) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.mp4', '.webm', '.mov', '.avi'))]
                if len(image_files) == 0: bg = None
                else:
                    random_image = random.choice(image_files)
                    if not random_image: bg = None
                    else:
                        if random_image.split(".")[-1].lower() in ["mp4", "webm", "mov", "avi"]:
                            bg = os.path.join(selected_config.get("bg_images_folder", ""), random_image)
                        else:
                            bg = Image.open(os.path.join(selected_config.get("bg_images_folder", ""), random_image)).copy()
                            if selected_config.get("remove_used_bg", False):
                                _safe_unlink(os.path.join(selected_config.get("bg_images_folder", ""), random_image))

        if selected_config.get("generate_background", False):
            bg = Image.new("RGBA", (int(background_width), int(background_height)))

            draw = ImageDraw.Draw(bg)
            draw.rectangle((0, 0, int(background_width), int(background_height)), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255))

            for _ in range(random.randint(10, 20)):
                x = int(background_width * random.uniform(0, 1))
                y = int(background_height * random.uniform(0, 1))
                w = 100 * random.uniform(0.1, 10)
                h = 100 * random.uniform(0.1, 10)
                start_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                end_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)

                for i in range(int(w)):
                    r = int(start_color[0] * (1 - i / w) + end_color[0] * (i / w))
                    g = int(start_color[1] * (1 - i / w) + end_color[1] * (i / w))
                    b = int(start_color[2] * (1 - i / w) + end_color[2] * (i / w))
                    col = (r, g, b, 255)

                    draw.line([(x + i, y), (x + i, y + h)], fill=col)

            for _ in range(random.randint(10, 20)):
                x = int(background_width * random.uniform(0, 1))
                y = int(background_height * random.uniform(0, 1))
                w = 100 * random.uniform(0.1, 3)
                h = 100 * random.uniform(0.1, 3)
                col = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                draw.ellipse((x, y, x + w, y + h), fill=col)

            del draw

        if bg is None and selected_config.get("ai_generation", False) and ai_image:
            try:
                bg = Image.open(io.BytesIO(ai_image)).copy()
            except Exception:
                print("Не удалось открыть ИИ фон, используется фон с сервера")
                bg = None

        if bg is None:
            for _ in range(10):
                try:
                    async with curl_cffi.AsyncSession() as session:
                        res = await session.get("https://api2.snaipix.com/unique/get_random_image", headers={"content-type": "image/png"}, timeout=30)
                        bg = Image.open(io.BytesIO(res.content))
                except:
                    print(f"Не удалось получить изображение заднего фона с сервера ({_+1}/10)")
                    continue

                break

        if isinstance(bg, Image.Image):

            if selected_config.get("mirror_x", False):
                bg = ImageOps.mirror(bg)
            if selected_config.get("mirror_y", False):
                bg = ImageOps.flip(bg)

            bg.save(tempFolder / tmp_file)
        else:
            tmp_file = tmp_file.replace(".png", ".mp4")
            shutil.copyfile(bg, tempFolder / tmp_file)
            if selected_config.get("remove_used_bg", False):
                _safe_unlink(bg)

    noise_tmp_file = "".join(random.choices(string.ascii_uppercase + string.digits, k=16)) + ".png"
    noise = np.random.rand(background_height, background_width, 3) * 255
    noise = noise.astype(np.uint8)
    noise_alpha_channel = np.full((background_height, background_width), int(255*selected_config.get("noise_intensity", 0)) if selected_config.get("noise_enabled", False) else 0, dtype=np.uint8)
    noise_image = Image.fromarray(np.dstack((noise, noise_alpha_channel)), 'RGBA')
    noise_width, noise_height = noise_image.size

    if selected_config.get("snow", False):
        tmp_snow_file = "".join(random.choices(string.ascii_uppercase + string.digits, k=16)) + ".png"
        snow_image = Image.new("RGBA", (background_width*1, background_height*4), color="#00000000")
        draw = ImageDraw.Draw(snow_image)

        custom_snow = False
        if selected_config.get("snow_dir", "") != "" and os.path.exists(selected_config.get("snow_dir", "")):
            if os.path.isfile(selected_config.get("snow_dir", "")):
                snow_files = [selected_config.get("snow_dir", "")]
            else:
                snow_files = [file for file in os.listdir(selected_config.get("snow_dir", "")) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'))]
            if len(snow_files) > 0:
                custom_snow = True

                for _ in range(selected_config.get("snow_count", 100)):
                    x = random.randint(0, background_width*1-1)
                    y = random.randint(0, background_height*4-1)
                    size = random.randint(int(selected_config.get("snow_size_min", 1)), int(selected_config.get("snow_size_max", 5)))
                    custom_snow_image = Image.open(f"{selected_config.get('snow_dir', '')}/{random.choice(snow_files)}").resize((size, size)).convert('RGBA')
                    snow_image.paste(custom_snow_image, (x, y), mask=custom_snow_image)

        if not custom_snow:
            for _ in range(selected_config.get("snow_count", 100)):
                x = random.randint(0, background_width*1-1)
                y = random.randint(0, background_height*4-1)
                r = random.randint(int(selected_config.get("snow_size_min", 1)), int(selected_config.get("snow_size_max", 5)))
                draw.ellipse((x-r, y-r, x+r, y+r), fill="white")

        snow_image.save(tempFolder / tmp_snow_file)

    draw = ImageDraw.Draw(noise_image)
    if selected_config.get("draw_lines", False):
        for y in np.arange(0, 1, 0.01):
            for x in np.arange(random.uniform(0, 0.3), 1, random.uniform(0.1, 0.3)):
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                draw.line((int(x * noise_width), int(y * noise_height), int(x * noise_width + int(selected_config.get("line_width", 0))), int(y * noise_height + int(selected_config.get("line_width", 0)))), fill=color, width=int(selected_config.get("line_thickness", 0)))

    if selected_config.get("enable_pixel", False):
        pixel_width, pixel_height = noise_image.size
        overlay = Image.new("RGBA", (pixel_width, pixel_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(0, pixel_height, int(selected_config.get("pixel_size", 16))):
            for x in range(0, pixel_width, int(selected_config.get("pixel_size", 16))):
                r = random.randint(0, 255)
                g = random.randint(0, 255)
                b = random.randint(0, 255)
                a = random.uniform(selected_config.get("pixel_opacity_min", 0), selected_config.get("pixel_opacity_max", 0.3))

                draw.rectangle([x, y, x + int(selected_config.get("pixel_size", 16)) - 1, y + int(selected_config.get("pixel_size", 16)) - 1], fill=(r, g, b, int(255*a)))
        noise_image = Image.alpha_composite(noise_image, overlay)

    if selected_config.get("emoji", False):
        async with curl_cffi.AsyncSession() as session:
            emojo_res = await session.get("https://api2.snaipix.com/unique/get_random_emoji", headers={"content-type": "image/png"}, timeout=30)
        emoji_image = Image.open(io.BytesIO(emojo_res.content))
        emoji_image = emoji_image.resize((int(32*selected_config.get("emoji_scale_factor", 1)), int(32*selected_config.get("emoji_scale_factor", 1))))

        emoji_data = emoji_image.getdata()
        emoji_new_data = []
        for item in emoji_data:
            emoji_new_data.append((item[0], item[1], item[2], int(item[3] * selected_config.get("emoji_opacity", 1))))
        emoji_image.putdata(emoji_new_data)

        for i in range(int(selected_config.get("emoji_count", 10))):
            noise_image.paste(emoji_image, (random.randint(0, background_width), random.randint(0, background_height)), mask=emoji_image.split()[-1])

    noise_image.save(tempFolder / noise_tmp_file)

    input_stream = ffmpeg.input(video_path, **input_args)
    input_video_audio = input_stream.audio
    input_video_stream = input_stream.video.filter('format', 'rgba')

    if get_audio_info(video_path) is None:
        input_video_audio = ffmpeg.input(f"anullsrc=cl=stereo:r=44100:d={duration}", f="lavfi")

    if selected_config.get("is_9_16", False):
        input_video_stream = input_video_stream.filter("scale", "1080", "-2")

    if selected_config.get("mirror_x", False):
        input_video_stream = input_video_stream.filter("hflip")
    if selected_config.get("mirror_y", False):
        input_video_stream = input_video_stream.filter("vflip")

    if selected_config.get("chromokey", False):
        color = selected_config.get("chromokey_color", "#000000")
        if len(color) > 7: color = color[:7]
        color = color.replace("#", "0x")
        input_video_stream = input_video_stream.filter("colorkey", color=color, similarity=round(selected_config.get("chromokey_similarity", 0.1), 2), blend=round(selected_config.get("chromokey_blend", 0), 2))

    noise_stream = ffmpeg.input(str(tempFolder / noise_tmp_file), loop=1, **input_args).filter("scale", width=background_width, height=background_height)





    if selected_config.get("watermark", False):
        text_positions = {
            "Слева сверху": ("10", "10"),
            "Вверху по центру": ("(w-text_w)/2", "10"),
            "Справа вверху": ("w-tw-10", "10"),
            "Слева внизу": ("10", "h-th-10"),
            "Внизу по центру": ("(w-text_w)/2", "h-th-10"),
            "Справа внизу": ("w-tw-10", "h-th-10"),
            "По центру": ("(w-text_w)/2", "(h-text_h)/2")
        }
        text_x, text_y = text_positions[selected_config.get("watermark_position", "Слева сверху")] if selected_config.get("watermark_position", "Слева сверху") in text_positions else random.choice(list(text_positions.values()))
        input_video_stream = input_video_stream.filter("drawtext", text=selected_config.get("watermark_text", "watermark"), fontfile=f"C:/Windows/fonts/{selected_config.get('watermark_font', 'ARIALN.TTF')}", fontcolor=f"0xFFFFFF{hex(int(selected_config.get('watermark_opacity', 1)*255))[2:].upper()}", fontsize=selected_config.get("watermark_size", 100), x=text_x, y=text_y)

    if selected_config.get("draw_text", False) and len(selected_config.get("draw_text_text", "").strip()) > 0:
        font_file = _pick_file(selected_config.get("draw_text_font", ""), (".ttf", ".otf")) or "C:/Windows/Fonts/arial.ttf"

        pos_x = random.uniform(selected_config.get("draw_text_pos_x_min", 0.5), selected_config.get("draw_text_pos_x_max", 0.5))
        pos_y = random.uniform(selected_config.get("draw_text_pos_y_min", 0.5), selected_config.get("draw_text_pos_y_max", 0.5))

        x_expr = f"w*{pos_x}"
        y_expr = f"h*{pos_y}"

        if selected_config.get("draw_text_move_x", False):
            x_expr = f"w*{pos_x}+{random.uniform(50, 250)}*sin(t*{random.uniform(0.5, 5)})"
        if selected_config.get("draw_text_move_y", False):
            y_expr = f"h*{pos_y}+{random.uniform(50, 250)}*sin(t*{random.uniform(0.5, 5)})"

        fontsize_expr = random.uniform(selected_config.get("draw_text_size_min", 100), selected_config.get("draw_text_size_max", 100))
        if selected_config.get("draw_text_dynamic_size", False):
            fontsize_expr = f"{fontsize_expr}+20*sin(t*{random.uniform(0.5, 2)})"

        text_color = selected_config.get("draw_text_color", "#FFFFFF") or "#FFFFFF"
        input_video_stream = input_video_stream.filter(
            "drawtext",
            text=generate_formatted_string(selected_config.get("draw_text_text", ""), {}),
            x=f"max(0,min(w-tw,{x_expr}-tw/2))",
            y=f"max(0,min(h-th,{y_expr}-th/2))",
            alpha=random.uniform(selected_config.get("draw_text_alpha_min", 1), selected_config.get("draw_text_alpha_max", 1)),
            fontfile=font_file.replace("\\", "/"),
            fontsize=fontsize_expr,
            fontcolor=text_color[:7].replace("#", "0x") if text_color.startswith("#") else text_color
        )

    if selected_config.get("apply_background", False):
        if tmp_file.endswith(".mp4"):
            background_info, background_audio_info = probe_video(str(tempFolder / tmp_file))
            background_duration = float(background_info["duration"])

            background = ffmpeg.input(str(tempFolder / tmp_file), **input_args)
            background_audio = background.audio
            background_stream = background.video

            if selected_config.get("clip", False) and background_duration > duration:
                rnd = random.uniform(0, 1)
                background_stream = background_stream.filter("trim", start=rnd*(background_duration-duration), duration=duration).filter("setpts", "PTS-STARTPTS")
                if background_audio_info is not None:
                    background_audio = background_audio.filter("atrim", start=rnd*(background_duration-duration), duration=duration).filter("asetpts", "PTS-STARTPTS")
            else:
                background_stream = background_stream.filter("trim", duration=duration)
                if background_audio_info is not None:
                    background_audio = background_audio.filter("atrim", duration=duration).filter("asetpts", "PTS-STARTPTS")


            if background_audio is not None:
                if selected_config.get("background_audio_volume", False):
                    background_audio = background_audio.filter("volume", random.uniform(selected_config.get("background_audio_volume_min", 0.5), selected_config.get("background_audio_volume_max", 1.5)))

                input_video_audio = ffmpeg.filter([input_video_audio, background_audio], "amix", inputs=2, duration="longest", dropout_transition=2)

        else:
            background_stream = ffmpeg.input(str(tempFolder / tmp_file), loop=1, **input_args).filter('format', 'yuv420p')

        if selected_config.get("video_position", "По центру") == "По центру":
            if selected_config.get("background_blur", False):
                background_stream = background_stream.filter("gblur", sigma=selected_config.get("background_blur_value", 0))
            if selected_config.get("zoom", False):
                speed = random.uniform(selected_config.get("zoom_speed_min", 0.1), selected_config.get("zoom_speed_max", 0.1))
                background_stream = background_stream.filter("zoompan", z=f"if(lte(mod(on,120),60),zoom+{speed},zoom-{speed})", x='iw/2-(iw/zoom)/2', y='ih/2-(ih/zoom)/2', d=25 * duration)
            background_stream = background_stream.filter("scale", width=background_width, height=background_height).filter("trim", duration=duration)

            x_offset = random.randint(0, int(background_width - width))
            y_offset = random.randint(0, int(background_height - height))

            if selected_config.get("is_9_16", False):
                x_offset = "(W-w)/2"
                y_offset = "(H-h)/2"
            elif not selected_config.get("random_position", False):
                x_offset = int(selected_config.get("background_size_left", 0))
                y_offset = int(selected_config.get("background_size_top", 0))

            if selected_config.get("rounded_border", False):
                radius = selected_config.get("border_radius", 40)
                input_video_stream = input_video_stream.filter("geq", lum='p(X,Y)', a=f"if(gt(abs(W/2-X),W/2-{radius})*gt(abs(H/2-Y),H/2-{radius}),if(lte(hypot({radius}-(W/2-abs(W/2-X)),{radius}-(H/2-abs(H/2-Y))),{radius}),255,0),255)")
            if selected_config.get("border", False):
                border_size = selected_config.get("border_size", 10)
                border_color = selected_config.get("border_color", "black")
                input_video_stream = input_video_stream.filter("pad", f"iw+{border_size}", f"ih+{border_size}", f"iw-{border_size}", f"ih-{border_size}", border_color)

            selected_config["image_opacity"] = random.uniform(selected_config.get("image_opacity_min", 1), selected_config.get("image_opacity_max", 1))
            if selected_config.get("image_opacity", 1) < 1:
                input_video_stream = input_video_stream.filter("colorchannelmixer", aa=selected_config.get("image_opacity", 1))

            if selected_config.get("smooth_appear", False):
                input_video_stream = input_video_stream.filter("tpad", start_duration=selected_config.get("smooth_appear_st", 3)).setpts("PTS-STARTPTS").filter("fade", type="in", start_time=selected_config.get("smooth_appear_st", 3), duration=selected_config.get("smooth_appear_dur", 5))
                input_video_audio = input_video_audio.filter("adelay", delays=f"{selected_config.get('smooth_appear_st', 3)*1000}|{selected_config.get('smooth_appear_st', 3)*1000}").filter('asetpts', 'PTS-STARTPTS').filter("afade", type="in", start_time=selected_config.get("smooth_appear_st", 3), duration=selected_config.get("smooth_appear_dur", 5))

            if selected_config.get("video_rotate", False):
                base_angle = math.radians(random.uniform(float(selected_config.get("video_rotate_min", 0)), float(selected_config.get("video_rotate_max", 0))))

                deg_amp = random.uniform(float(selected_config.get("video_rotate_deg_min", 1)), float(selected_config.get("video_rotate_deg_max", 1)))
                speed = random.uniform(float(selected_config.get("video_rotate_speed_min", 1)), float(selected_config.get("video_rotate_speed_max", 1)))
                direction = random.choice([-1, 1])
                amp = math.radians(deg_amp)

                angle_expr = f"{base_angle}+{direction}*{amp}*sin(2*PI*{speed}*t)"
                size_expr = "ceil(hypot(iw,ih)/2)*2"

                input_video_stream = input_video_stream.filter("format", "rgba")
                input_video_stream = input_video_stream.filter(
                    "rotate",
                    angle_expr,
                    out_w=size_expr,
                    out_h=size_expr,
                    fillcolor="0x00000000@0"
                )

            if selected_config.get("video_perspective", False):
                top_amount = random.uniform(float(selected_config.get("video_perspective_top_min", 0.2)), float(selected_config.get("video_perspective_top_max", 0.2)))
                bottom_amount = random.uniform(float(selected_config.get("video_perspective_bottom_min", 0.2)), float(selected_config.get("video_perspective_bottom_max", 0.2)))
                left_amount = random.uniform(float(selected_config.get("video_perspective_left_min", 0.2)), float(selected_config.get("video_perspective_left_max", 0.2)))
                right_amount = random.uniform(float(selected_config.get("video_perspective_right_min", 0.2)), float(selected_config.get("video_perspective_right_max", 0.2)))

                top_speed = random.uniform(float(selected_config.get("video_perspective_top_speed_min", 1.0)), float(selected_config.get("video_perspective_top_speed_max", 1.0)))
                bottom_speed = random.uniform(float(selected_config.get("video_perspective_bottom_speed_min", 1.0)), float(selected_config.get("video_perspective_bottom_speed_max", 1.0)))
                left_speed = random.uniform(float(selected_config.get("video_perspective_left_speed_min", 1.0)), float(selected_config.get("video_perspective_left_speed_max", 1.0)))
                right_speed = random.uniform(float(selected_config.get("video_perspective_right_speed_min", 1.0)), float(selected_config.get("video_perspective_right_speed_max", 1.0)))

                top_shift = f"{top_amount}*sin({top_speed}*0.1*on)"
                bottom_shift = f"{bottom_amount}*sin({bottom_speed}*0.1*on)"
                left_shift = f"{left_amount}*sin({left_speed}*0.1*on)"
                right_shift = f"{right_amount}*sin({right_speed}*0.1*on)"

                x0 = f"W*({top_shift})"
                x1 = f"W*(1-({top_shift}))"
                x2 = f"W*({bottom_shift})"
                x3 = f"W*(1-({bottom_shift}))"

                y0 = f"H*({left_shift})"
                y2 = f"H*(1-({left_shift}))"
                y1 = f"H*({right_shift})"
                y3 = f"H*(1-({right_shift}))"

                pad_w = "ceil(iw*1.5/2)*2"
                pad_h = "ceil(ih*1.5/2)*2"

                input_video_stream = input_video_stream.filter("pad", pad_w, pad_h, "(ow-iw)/2", "(oh-ih)/2", "0x00000000@0").filter(
                    "perspective",
                    x0=x0, y0=y0,
                    x1=x1, y1=y1,
                    x2=x2, y2=y2,
                    x3=x3, y3=y3,
                    sense="destination",
                    eval="frame",
                    interpolation="linear",
                )


            output_stream = ffmpeg.overlay(background_stream, input_video_stream, format="auto", x=f"max(0,min(W-w,(W-w)/2+(W/4-W/8)*sin({selected_config.get('speed_x', 1)}*PI*t/{selected_config.get('oscillations_x', 2)})))" if selected_config.get("move_x", False) else x_offset, y=f"max(0,min(H-h,(H-h)/2+(H/4-H/8)*sin({selected_config.get('speed_y', 1)}*PI*t/{selected_config.get('oscillations_y', 4)})))" if selected_config.get("move_y", False) else y_offset)
        elif selected_config.get("video_position", "По центру") == "Сверху":
            background_stream = background_stream.filter("scale", width, -1).filter("trim", duration=duration)
            output_stream = ffmpeg.filter([input_video_stream, background_stream], "vstack")
        elif selected_config.get("video_position", "По центру") == "Снизу":
            background_stream = background_stream.filter("scale", width, -1).filter("trim", duration=duration)
            output_stream = ffmpeg.filter([background_stream, input_video_stream], "vstack")
        elif selected_config.get("video_position", "По центру") == "Слева":
            background_stream = background_stream.filter("scale", -1, height).filter("trim", duration=duration)
            output_stream = ffmpeg.filter([input_video_stream, background_stream], "hstack")
        elif selected_config.get("video_position", "По центру") == "Справо":
            background_stream = background_stream.filter("scale", -1, height).filter("trim", duration=duration)
            output_stream = ffmpeg.filter([background_stream, input_video_stream], "hstack")
    else:
        output_stream = input_video_stream

    if selected_config.get("grid_mask", False) and len(selected_config.get("grid_mask_folder", "")) > 0 and os.path.exists(selected_config.get("grid_mask_folder", "")):
        if os.path.isfile(selected_config.get("grid_mask_folder", "")):
            grid_mask_files = [selected_config.get("grid_mask_folder", "")]
        else:
            grid_mask_files = [file for file in os.listdir(selected_config.get("grid_mask_folder", "")) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'))]

        if grid_mask_files:
            grid_mask_file = random.choice(grid_mask_files)
            zoomscale = random.uniform(selected_config.get('grid_mask_scale_min', 0.001), selected_config.get('grid_mask_scale_max', 0.005))
            grid_mask_stream = ffmpeg.input(os.path.join(selected_config.get("grid_mask_folder", ""), grid_mask_file), **input_args).filter(
                "zoompan",
                z = f"if(lte(mod(on+{random.randint(0, 10)},120),60),zoom+{zoomscale}*sin(on*0.05),zoom-{zoomscale}*cos(on*0.07))",
                x="iw/2-(iw/zoom)/2",
                y="ih/2-(ih/zoom)/2",
                s=f"{int(background_width*1.5)}x{int(background_height*1.5)}",
                d=25 * duration
            )

            mask_w = int(background_width * 1.5)
            mask_h = int(background_height * 1.5)
            video_w = background_width
            video_h = background_height

            x_min = video_w - mask_w
            y_min = video_h - mask_h

            amp_x = abs(x_min) // 2
            amp_y = abs(y_min) // 2

            speed = random.uniform(selected_config.get('grid_mask_speed_min', 0.1), selected_config.get('grid_mask_speed_max', 1))

            freq_x = round(random.uniform(0.008, 0.015) * speed, 5)
            freq_y = round(random.uniform(0.008, 0.015) * speed, 5)
            phase_x = round(random.uniform(0, 6.28), 5)
            phase_y = round(random.uniform(0, 6.28), 5)

            x_expr = f"{x_min // 2} + {amp_x}*sin(n*{freq_x}+{phase_x})"
            y_expr = f"{y_min // 2} + {amp_y}*cos(n*{freq_y}+{phase_y})"

            output_stream = ffmpeg.overlay(output_stream, grid_mask_stream, x=x_expr, y=y_expr)

    output_stream = ffmpeg.overlay(output_stream, noise_stream, shortest=1, x=0, y=0)

    if selected_config.get("set_brightness", False):
        output_stream = output_stream.filter("eq", brightness=random.uniform(selected_config.get("brightness_min", -0.1), selected_config.get("brightness_max", 0.1)))

    if selected_config.get("fadein", False):
        output_stream = output_stream.filter("fade", type="in", duration=selected_config.get("fadein_duration", 5))

    if selected_config.get("fadeout", False):
        output_stream = output_stream.filter("fade", type="out", start_time=duration-selected_config.get("fadeout_duration", 5), duration=selected_config.get("fadeout_duration", 5))

    if selected_config.get("snow", False):
        snow_stream = ffmpeg.input(str(tempFolder / tmp_snow_file), loop=1, **input_args).filter("trim", duration=duration)
        output_stream = ffmpeg.overlay(output_stream, snow_stream, shortest=1, x="40*sin(t*2*PI/5)", y=f"((H+{background_height})*-cos(t*0.1*PI/3))-({background_height*2}-H/2)")

    if selected_config.get("particle", False):
        offset_between = int(background_width / (selected_config.get("particle_count", 10)-1))
        for particle_index in range(selected_config.get("particle_count", 10)):
            particle_stream = ffmpeg.input(str(tempFolder / tmp_particle_file), loop=1, **input_args).filter("trim", duration=duration).filter_multi_output('split').stream(particle_index)
            output_stream = ffmpeg.overlay(output_stream, particle_stream, shortest=1, x=f"{int(offset_between*particle_index)}+{offset_between}*sin(t*2*PI/5)", y=f"H/2+H/2*cos(t*{random.uniform(0, 1)}*PI/3)")

    if selected_config.get("dynamic_noise", False):
        output_stream = output_stream.filter('noise', alls=5, allf="t+u")

    if selected_config.get("random_speed", False):
        def process_video_speed(stream, start, end, expr, stream_no):
            return stream.filter_multi_output('split').stream(stream_no).trim(start=start, end=end).setpts(expr).setpts('PTS-STARTPTS')

        parts = []
        audio_parts = []
        speed_up = random.randint(0, 1) == 1
        stream_no = 0
        for start, end in split_number(duration, selected_config.get("random_speed_segments", 6)):
            speedval = random.uniform(selected_config.get('random_speed_min', 1), selected_config.get('random_speed_max', 2))
            parts.append(process_video_speed(output_stream, start, end, f"PTS/{speedval}" if speed_up else f"{speedval}*PTS", stream_no))
            audio_parts.append(ffmpeg.input(video_path, **input_args).audio.filter("atrim", start=start, end=end).filter("atempo", speedval if speed_up else f"1/{speedval}").filter('asetpts', 'PTS-STARTPTS'))
            stream_no += 1
            speed_up = not speed_up

        output_stream = ffmpeg.concat(*parts, v=1, a=0).node[0]
        input_video_audio = ffmpeg.concat(*audio_parts, v=0, a=1).node[0]

    if selected_config.get("video_position", "По центру") in ["Справо", "Слева"]:
        output_stream = output_stream.filter("scale", 1920, -1)
    elif selected_config.get("video_position", "По центру") in ["Снизу", "Сверху"]:
        output_stream = output_stream.filter("scale", -1, 1920)
    else:
        if selected_config.get("video_quality", "Не изменять") != "Не изменять":
            video_quality = int(selected_config.get("video_quality", "720p").replace("p", ""))

            if width > height:
                output_stream = output_stream.filter("scale", -1, video_quality)
            else:
                output_stream = output_stream.filter("scale", video_quality, -1)

    output_stream = output_stream.filter("scale", width="trunc(iw/2)*2", height="trunc(ih/2)*2")
    output_stream = output_stream.filter('fps', fps=25, round='up')

    metadata = {
        "metadata:g:0": f"major_brand=mp42"
    }


    codec_params = {
        "movflags": "faststart"
    }

    fastest_preset = {
        "libx264": "veryfast",
        "h264_nvenc": "p4",
        "h264_amf": "balanced",
    }

    codec_params["preset"] = fastest_preset.get(video_encoder, "p4")

    if video_encoder == "libx264":
        codec_params.update({
            "crf": {"Легкое": 18, "Среднее": 22, "Высокое": 26}[selected_config.get("compression_level", "Среднее")],
            "pix_fmt": "yuv420p"
        })

    elif video_encoder == "h264_nvenc":
        codec_params.update({
            "rc": "vbr",
            "cq": 22,
            "b:v": "0",
            "maxrate": "8M",
            "bufsize": "16M",
            "pix_fmt": "yuv420p"
        })

    elif video_encoder == "h264_amf":
        codec_params.update({
            "quality": "balanced",
            "rc": "cqp",
            "qp_i": 22,
            "qp_p": 23,
            "qp_b": 25,
            "pix_fmt": "yuv420p"
        })

    else:
        codec_params.update({
            "qp": 23,
            "pix_fmt": "yuv420p"
        })

    try:
        if selected_config.get("random_audio", False):
            if selected_config.get("audio_random_volume", False):
                input_video_audio = input_video_audio.filter("volume", random.uniform(selected_config.get("audio_random_volume_min", 0.7), selected_config.get("audio_random_volume_max", 1.5)))
            if selected_config.get("audio_music", False) and len(selected_config.get("audio_music_path", "")) > 0 and os.path.exists(selected_config.get("audio_music_path", "")):
                if os.path.isfile(selected_config.get("audio_music_path", "")):
                    audio_files = [selected_config.get("audio_music_path", "")]
                else:
                    audio_files = sorted(file for file in os.listdir(selected_config.get("audio_music_path", "")) if file.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')))
            else:
                audio_files = []
            if audio_files:
                audio_files = audio_files[render_index % len(audio_files)]
                music_info = get_audio_info(os.path.join(selected_config.get("audio_music_path", ""), audio_files))

                music_stream = ffmpeg.input(os.path.join(selected_config.get("audio_music_path", ""), audio_files))
                if music_info is not None and float(music_info.get("duration", "0")) > duration and selected_config.get("music_clip", False):
                    music_stream = music_stream.filter("volume", random.uniform(selected_config.get("music_volume_min", 1), selected_config.get("music_volume_max", 1))).filter("atrim", start=random.uniform(0, 1)*(float(music_info.get("duration", "0"))-duration), duration=duration).filter("asetpts", "PTS-STARTPTS")
                else:
                    music_stream = music_stream.filter("volume", random.uniform(selected_config.get("music_volume_min", 1), selected_config.get("music_volume_max", 1))).filter("atrim", duration=duration)
                input_video_audio = ffmpeg.filter([input_video_audio, music_stream], "amix", inputs=2, duration="longest")
            if selected_config.get("audio_noise", False):
                noise_audio = ffmpeg.input(f"anoisesrc=a={random.uniform(selected_config.get('audio_noise_volume_min', 0.1), selected_config.get('audio_noise_volume_max', 0.3))}:c={random.choice(['white', 'pink', 'brown', 'blue', 'violet', 'velvet'])}", f='lavfi', t=duration).filter("volume", random.uniform(0.1, 0.3))
                input_video_audio = ffmpeg.filter([input_video_audio, noise_audio], "amix", inputs=2, duration="longest")


        final_stream = ffmpeg.output(output_stream, input_video_audio, dist_path, acodec="aac", vcodec=video_encoder, **codec_params, map_metadata="-1", **{"flags:v": "+bitexact", "flags:a": "+bitexact"})
        out, err = ffmpeg.run(final_stream, cmd=FFMPEG_PATH, overwrite_output=True, quiet=not selected_config.get("preview", False))
    except Exception as e:
        print(f"Не удалось срендерить видео со звуком, повтор без звука: {e.stderr.decode(errors='ignore')[-500:] if isinstance(e, Error) and e.stderr else repr(e)}")

        try:
            final_stream = ffmpeg.output(output_stream, dist_path, vcodec=video_encoder, **codec_params, map_metadata="-1", **{"flags:v": "+bitexact"})
            out, err = ffmpeg.run(final_stream, cmd=FFMPEG_PATH, overwrite_output=True, quiet=not selected_config.get("preview", False))
        except Error as e:
            print(e.stderr.decode(errors="ignore") if e.stderr else repr(e))
            raise



    try:
        if selected_config.get("apply_background", False):
            Path(tempFolder / tmp_file).unlink()
    except Exception as e: pass
    try:
        if selected_config.get("snow", False):
            Path(tempFolder / tmp_snow_file).unlink()
    except Exception as e: pass
    try:
        if selected_config.get("particle", False):
            Path(tempFolder / tmp_particle_file).unlink()
    except Exception as e: pass
    try:
        Path(tempFolder / noise_tmp_file).unlink()
    except Exception as e: pass

    if selected_config.get("random_metadata", False):
        try:
            randomize_video_metadata(dist_path)
        except Exception:
            print(traceback.format_exc())

    return dist_path




def _safe_unlink(path):
    try:
        os.unlink(path)
    except Exception:
        pass


def _pick_file(path: str, extensions: tuple) -> str | None:
    if not path or not os.path.exists(path):
        return None
    if os.path.isfile(path):
        return path

    files = [f for f in os.listdir(path) if f.lower().endswith(extensions)]
    if not files:
        return None

    return os.path.join(path, random.choice(files))


def _brand4(value: str) -> bytes:
    return value.encode("ascii", errors="ignore")[:4].ljust(4, b" ")


def _patch_ftyp_inplace(data: bytearray) -> bool:
    pos = data.find(b"ftyp", 4, 4096)
    if pos < 4:
        return False

    atom_start = pos - 4
    atom_size = struct.unpack(">I", data[atom_start:atom_start + 4])[0]
    atom_end = atom_start + atom_size
    if atom_size < 16 or atom_end > len(data):
        return False

    major_pos = pos + 4
    minor_pos = major_pos + 4
    compat_pos = minor_pos + 4
    slot_count = (atom_end - compat_pos) // 4

    data[major_pos:major_pos + 4] = _brand4("qt  ")
    data[minor_pos:minor_pos + 4] = struct.pack(">I", 512)
    data[compat_pos:compat_pos + slot_count * 4] = _brand4("qt  ") * slot_count
    return True


def _patch_quicktime_creation_times_inplace(data: bytearray, timestamp: int) -> int:
    packed = struct.pack(">I", timestamp + 2082844800)

    total = 0
    for atom_type in (b"mvhd", b"tkhd", b"mdhd"):
        start = 0
        while True:
            pos = data.find(atom_type, start)
            if pos < 4:
                break

            atom_size = struct.unpack(">I", data[pos - 4:pos])[0]
            if atom_size >= 24 and data[pos + 4] == 0:
                data[pos + 8:pos + 12] = packed
                data[pos + 12:pos + 16] = packed
                total += 1

            start = pos + 1
    return total


def _patch_avc1_compressor_name_inplace(data: bytearray) -> int:
    count = 0
    start = 0
    while True:
        pos = data.find(b"avc1", start)
        if pos < 4:
            break

        atom_start = pos - 4
        atom_size = struct.unpack(">I", data[atom_start:atom_start + 4])[0]
        if 80 < atom_size < 1000 and atom_start + 82 <= len(data):
            data[atom_start + 50:atom_start + 82] = b"\x00" * 32
            count += 1

        start = pos + 1
    return count


def _replace_same_size_all(data: bytearray, pattern: bytes, replacement: str) -> int:
    repl_raw = replacement.encode("utf-8", errors="ignore")
    matches = list(re.finditer(pattern, data))
    for m in matches:
        size = m.end() - m.start()
        data[m.start():m.end()] = repl_raw[:size].ljust(size, b"\x00")
    return len(matches)


def randomize_video_metadata(path: str):
    data = bytearray(Path(path).read_bytes())
    timestamp = int(time.time()) - random.randint(60, 5 * 3600)

    _patch_ftyp_inplace(data)
    _patch_quicktime_creation_times_inplace(data, timestamp)
    _patch_avc1_compressor_name_inplace(data)
    _replace_same_size_all(data, rb"Lavf\d+\.\d+\.\d+", "Lavf61.1.100")
    _replace_same_size_all(data, rb"Lavc\d+\.\d+\.\d+(?: libx264)?", "Lavc61.3.100")
    _replace_same_size_all(data, rb"x264 - core [^\x00]{20,900}", "")

    Path(path).write_bytes(data)


def _index_sort_key(path: str):
    name = os.path.basename(path)
    prefix = name.split("_", 1)[0].split(".", 1)[0]
    return (0, int(prefix), name) if prefix.isdigit() else (1, 0, name)


def collect_unique_sources(creo_path: str) -> tuple[str, list[str]]:
    """Returns (source_type, files) where source_type is "video", "photo_layers" or "photo"."""
    if not creo_path or not os.path.isdir(creo_path):
        return "", []

    files = [
        os.path.join(creo_path, f) for f in os.listdir(creo_path)
        if os.path.isfile(os.path.join(creo_path, f)) and "_tmp." not in f.lower()
    ]

    videos = sorted((f for f in files if f.lower().endswith(VIDEO_EXTENSIONS)), key=_index_sort_key)
    if videos:
        return "video", videos

    layers = sorted((f for f in files if f.lower().endswith(".photo.unique")), key=_index_sort_key)
    if layers:
        return "photo_layers", layers

    photos = sorted((f for f in files if f.lower().endswith(PHOTO_EXTENSIONS)), key=_index_sort_key)
    if photos:
        return "photo", photos

    return "", []


def render_unique_photo(source: str, dist_path: str):
    if source.lower().endswith(".photo.unique"):
        with open(source, "r", encoding="utf-8") as f:
            img = asyncio.run(get_preview(json.load(f)))
    else:
        with Image.open(source) as original:
            img = ImageOps.exif_transpose(original).convert("RGB")

        w, h = img.size
        crop = random.uniform(0.01, 0.03)
        left, top = int(w * crop * random.random()), int(h * crop * random.random())
        img = img.crop((left, top, left + int(w * (1 - crop)), top + int(h * (1 - crop)))).resize((w, h), Image.LANCZOS)

    if img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size
    img.save(
        dist_path,
        format="JPEG",
        quality=random.randint(88, 95),
        optimize=True,
        progressive=True,
        subsampling=0,
        exif=random_exif_bytes(width, height, add_gps=False),
        icc_profile=base64.b64decode(DISPLAY_P3_ICC_B64)
    )
    img.close()

    return dist_path


def preview_unique_video(preset: dict):
    try:
        source_type, files = collect_unique_sources(preset.get("creo_path", ""))
        if source_type != "video":
            return False

        TEMP_PATH.mkdir(parents=True, exist_ok=True)
        dist_path = str(TEMP_PATH / f"preview_{uuid.uuid4().hex[:8]}.mp4")

        print(f"Preview: {files[0]}")
        asyncio.run(video_unique_new(files[0], dist_path, preset.copy() | {"remove_used_bg": False, "preview": True}, 0))

        if platform.system() == "Windows":
            os.startfile(dist_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", dist_path])
        else:
            subprocess.run(["xdg-open", dist_path])
        return True
    except Exception:
        print(traceback.format_exc())
        return False


class UniqueJob:

    def __init__(self, preset: dict, output_dir: str, files_count: int, threads: int):
        self.preset = preset.copy()
        self.files_count = max(1, int(files_count))
        self.threads = max(1, int(threads))
        self.base_output_dir = output_dir
        self.output_dir = ""
        self.total = 0
        self.done = 0
        self.failed = 0
        self.running = False
        self.stopped = False
        self.error = ""
        self._lock = threading.Lock()

    def status(self) -> dict:
        return {
            "running": self.running,
            "total": self.total,
            "done": self.done,
            "failed": self.failed,
            "stopped": self.stopped,
            "error": self.error,
            "output_dir": self.output_dir,
        }

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.stopped = True

    def _run(self):
        try:
            source_type, files = collect_unique_sources(self.preset.get("creo_path", ""))
            if not files:
                self.error = "no_files"
                return

            folder_name = re.sub(r'[<>:"/\\|?*]', "_", self.preset.get("name", "unique")).strip() or "unique"
            output_dir = Path(self.base_output_dir) / f"{folder_name}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
            output_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir = str(output_dir)

            tasks = []
            for i in range(self.files_count):
                for k, source in enumerate(files):
                    if source_type == "video":
                        dist_path = output_dir / (f"{i + 1}.mp4" if len(files) == 1 else f"{i + 1}_{k + 1}.mp4")
                    elif source_type == "photo_layers" and len(files) > 1:
                        (output_dir / str(i + 1)).mkdir(exist_ok=True)
                        dist_path = output_dir / str(i + 1) / f"{k + 1}.jpg"
                    else:
                        dist_path = output_dir / (f"{i + 1}.jpg" if len(files) == 1 else f"{i + 1}_{k + 1}.jpg")

                    tasks.append((source_type, source, str(dist_path), i * len(files) + k))

            self.total = len(tasks)

            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                list(executor.map(self._process, tasks))
        except Exception as e:
            self.error = repr(e)
            print(traceback.format_exc())
        finally:
            self.running = False

    def _process(self, task):
        if self.stopped:
            return

        source_type, source, dist_path, render_index = task

        try:
            if source_type == "video":
                asyncio.run(video_unique_new(source, dist_path, self.preset.copy(), render_index))
            else:
                render_unique_photo(source, dist_path)

            if not os.path.exists(dist_path) or os.path.getsize(dist_path) == 0:
                raise Exception("Output file was not created")

            with self._lock:
                self.done += 1
        except Exception:
            print(traceback.format_exc())
            with self._lock:
                self.failed += 1
