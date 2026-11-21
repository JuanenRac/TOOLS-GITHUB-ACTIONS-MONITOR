# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A small QR code writer with no packages: byte mode, error correction level M, versions 1 to 10 (up to 213 bytes), all eight masks tried and the best one kept.

  matrix(text)   the code as a list of rows of booleans (True = dark), without the quiet zone
  svg(text)      the same as an SVG drawing with a quiet zone of four modules, ready to put in a page (dark on white, so any scanner reads it in any theme)

It is used by the pairing of a phone (security/devices.py): the address that the code carries is short, so the limit is never reached; a longer text raises ValueError.
Written from the public specification (ISO/IEC 18004); nothing is copied from another program."""

ECC_PER_BLOCK = (10, 16, 26, 18, 24, 16, 18, 22, 22, 26)      # level M, versions 1 to 10
BLOCKS = (1, 1, 1, 2, 2, 4, 4, 4, 5, 5)
TOTAL_WORDS = (26, 44, 70, 100, 134, 172, 196, 242, 292, 346)
ALIGN = ((), (6, 18), (6, 22), (6, 26), (6, 30), (6, 34), (6, 22, 38), (6, 24, 42), (6, 26, 46), (6, 28, 50))
MAX_VERSION = 10

_EXP = [0] * 512
_LOG = [0] * 256
_value = 1
for _i in range(255):
    _EXP[_i] = _value
    _LOG[_value] = _i
    _value <<= 1
    if _value & 0x100:
        _value ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _generator(degree):
    poly = [1]
    for i in range(degree):
        nxt = [0] * (len(poly) + 1)
        for j, coef in enumerate(poly):
            nxt[j] ^= coef
            nxt[j + 1] ^= _mul(coef, _EXP[i])
        poly = nxt
    return poly


def _remainder(data, degree):
    gen = _generator(degree)
    rest = list(data) + [0] * degree
    for i in range(len(data)):
        factor = rest[i]
        if factor:
            for j in range(1, len(gen)):
                rest[i + j] ^= _mul(gen[j], factor)
    return rest[len(data):]


def _data_words(version):
    return TOTAL_WORDS[version - 1] - ECC_PER_BLOCK[version - 1] * BLOCKS[version - 1]


def _codewords(raw, version):
    """The data bits (mode, length, bytes, padding) cut in blocks, each with its error correction, interleaved."""
    bits = [0, 1, 0, 0]
    count_bits = 8 if version < 10 else 16
    bits += [(len(raw) >> (count_bits - 1 - i)) & 1 for i in range(count_bits)]
    for byte in raw:
        bits += [(byte >> (7 - i)) & 1 for i in range(8)]
    capacity = _data_words(version) * 8
    bits += [0] * min(4, capacity - len(bits))
    bits += [0] * (-len(bits) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(words) < _data_words(version):
        words.append(pad)
        pad = 0x11 if pad == 0xEC else 0xEC
    blocks_n, ecc_n = BLOCKS[version - 1], ECC_PER_BLOCK[version - 1]
    short = _data_words(version) // blocks_n
    long_blocks = _data_words(version) % blocks_n
    blocks, at = [], 0
    for b in range(blocks_n):
        size = short + (1 if b >= blocks_n - long_blocks else 0)
        blocks.append(words[at:at + size])
        at += size
    eccs = [_remainder(block, ecc_n) for block in blocks]
    out = []
    for i in range(short + 1):
        for block in blocks:
            if i < len(block):
                out.append(block[i])
    for i in range(ecc_n):
        for ecc in eccs:
            out.append(ecc[i])
    return out


def _bch(value, poly, bits_total, check_bits):
    rest = value << check_bits
    for i in range(bits_total - 1, check_bits - 1, -1):
        if rest >> i & 1:
            rest ^= poly << (i - check_bits)
    return rest


def _format_bits(mask):
    data = (0b00 << 3) | mask      # level M is 00
    return ((data << 10) | _bch(data, 0x537, 15, 10)) ^ 0x5412


def _version_bits(version):
    return (version << 12) | _bch(version, 0x1F25, 18, 12)


def _frame(version):
    """The grid with the fixed parts drawn: (modules, is_function)."""
    size = version * 4 + 17
    grid = [[False] * size for _ in range(size)]
    fixed = [[False] * size for _ in range(size)]

    def put(x, y, dark):
        grid[y][x] = dark
        fixed[y][x] = True

    for i in range(size):
        put(6, i, i % 2 == 0)
        put(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < size and 0 <= y < size:
                    dist = max(abs(dx), abs(dy))
                    put(x, y, dist not in (2, 4))
    positions = ALIGN[version - 1]
    for cy in positions:
        for cx in positions:
            if (cx == 6 and cy == 6) or (cx == 6 and cy == positions[-1]) or (cx == positions[-1] and cy == 6):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    put(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)
    for i in range(9):      # the places of the format information (written for real later)
        fixed[8][i] = fixed[i][8] = True
    for i in range(8):
        fixed[8][size - 1 - i] = True
        fixed[size - 1 - i][8] = True
    put(8, size - 8, True)      # the dark module
    if version >= 7:
        bits = _version_bits(version)
        for i in range(18):
            dark = bits >> i & 1 == 1
            a, b = size - 11 + i % 3, i // 3
            put(a, b, dark)
            put(b, a, dark)
    return grid, fixed


def _place(grid, fixed, words):
    size = len(grid)
    bits = [(w >> (7 - i)) & 1 for w in words for i in range(8)]
    at = 0
    x = size - 1
    up = True
    while x > 0:
        if x == 6:
            x -= 1
        for step in range(size):
            y = size - 1 - step if up else step
            for dx in (0, 1):
                xx = x - dx
                if not fixed[y][xx]:
                    grid[y][xx] = bits[at] == 1 if at < len(bits) else False
                    at += 1
        up = not up
        x -= 2


MASKS = (lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0, lambda x, y: (x + y) % 3 == 0,
         lambda x, y: (x // 3 + y // 2) % 2 == 0, lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
         lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0)


def _apply(grid, fixed, mask, version):
    size = len(grid)
    out = [row[:] for row in grid]
    for y in range(size):
        for x in range(size):
            if not fixed[y][x] and MASKS[mask](x, y):
                out[y][x] = not out[y][x]
    bits = _format_bits(mask)
    # the first copy, around the top-left finder, in the order of the specification
    for i in range(15):
        dark = bits >> i & 1 == 1
        if i <= 5:
            out[i][8] = dark
        elif i == 6:
            out[7][8] = dark
        elif i == 7:
            out[8][8] = dark
        elif i == 8:
            out[8][7] = dark
        else:
            out[8][14 - i] = dark
    # the second copy, split between the other two finders
    for i in range(15):
        dark = bits >> i & 1 == 1
        if i < 8:
            out[8][size - 1 - i] = dark
        else:
            out[size - 15 + i][8] = dark
    out[size - 8][8] = True
    return out


def _penalty(grid):
    size = len(grid)
    score = 0
    for lines in (grid, [list(col) for col in zip(*grid)]):
        for row in lines:
            run = 1
            for i in range(1, size):
                if row[i] == row[i - 1]:
                    run += 1
                    if i == size - 1 and run >= 5:
                        score += 3 + run - 5
                else:
                    if run >= 5:
                        score += 3 + run - 5
                    run = 1
            text = "".join("1" if v else "0" for v in row)
            score += 40 * (text.count("10111010000") + text.count("00001011101"))
    for y in range(size - 1):
        for x in range(size - 1):
            if grid[y][x] == grid[y][x + 1] == grid[y + 1][x] == grid[y + 1][x + 1]:
                score += 3
    dark = sum(v for row in grid for v in row)
    percent = dark * 100 / (size * size)
    score += int(abs(percent - 50) // 5) * 10
    return score


def matrix(text):
    """The QR code of `text` (UTF-8 bytes) as rows of booleans; ValueError when it does not fit in version 10."""
    raw = text.encode("utf-8")
    version = 0
    for v in range(1, MAX_VERSION + 1):
        count_bits = 8 if v < 10 else 16
        if 4 + count_bits + 8 * len(raw) <= _data_words(v) * 8:
            version = v
            break
    if not version:
        raise ValueError("text too long for the QR code of this monitor")
    grid, fixed = _frame(version)
    _place(grid, fixed, _codewords(raw, version))
    best = min((_apply(grid, fixed, mask, version) for mask in range(8)), key=_penalty)
    return best


def svg(text, module=6, label=""):
    """The code as an SVG: dark modules on white with a quiet zone of four modules."""
    rows = matrix(text)
    size = len(rows)
    side = (size + 8) * module
    cells = "".join(f'<rect x="{(x + 4) * module}" y="{(y + 4) * module}" width="{module}" height="{module}"/>' for y, row in enumerate(rows) for x, dark in enumerate(row) if dark)
    title = f"<title>{label}</title>" if label else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" width="{side}" height="{side}" role="img" shape-rendering="crispEdges">{title}'
            f'<rect width="{side}" height="{side}" fill="#fff"/><g fill="#000">{cells}</g></svg>')
