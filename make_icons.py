# 한우 수첩 앱 아이콘(icon-192.png, icon-512.png)을 표준 라이브러리만으로 그린다.
# 초록 바탕에 갈색 한우 얼굴(뿔, 귀, 얼굴, 주둥이, 눈)
import struct, zlib

BG = (31, 122, 61)
HORN = (240, 222, 180)
HEAD = (178, 108, 52)
EAR = (160, 94, 44)
MUZZLE = (236, 196, 160)
DARK = (40, 28, 20)


def ell(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def pixel(x, y):
    for cx, cy in ((0.45, 0.66), (0.55, 0.66)):
        if ell(x, y, cx, cy, 0.022, 0.03):
            return DARK
    if ell(x, y, 0.5, 0.65, 0.15, 0.1):
        return MUZZLE
    for cx in (0.41, 0.59):
        if ell(x, y, cx, 0.47, 0.03, 0.03):
            return DARK
    if ell(x, y, 0.5, 0.5, 0.19, 0.25):
        return HEAD
    for cx in (0.27, 0.73):
        if ell(x, y, cx, 0.4, 0.11, 0.055):
            return EAR
    for cx, sx in ((0.37, -1), (0.63, 1)):
        if ell(x, y, cx + sx * 0.03, 0.25, 0.035, 0.08):
            return HORN
    return BG


def png(size, path):
    ss = 3  # 가장자리 부드럽게(슈퍼샘플링)
    raw = bytearray()
    for j in range(size):
        raw.append(0)
        for i in range(size):
            acc = [0, 0, 0]
            for a in range(ss):
                for b in range(ss):
                    c = pixel((i + (a + .5) / ss) / size, (j + (b + .5) / ss) / size)
                    for k in range(3):
                        acc[k] += c[k]
            raw += bytes(v // (ss * ss) for v in acc)
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)) \
        + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    open(path, 'wb').write(data)


if __name__ == '__main__':
    png(192, 'icon-192.png')
    png(512, 'icon-512.png')
