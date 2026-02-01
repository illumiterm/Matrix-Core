#!/usr/bin/env python3

# MIT License

# Copyright (c) 2022 Elijah Gordon (NitrixXero) <nitrixxero@gmail.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import random
import time
import argparse
import shutil
import string
from colorama import init, Fore, Style

init(autoreset=False)

ANSI_PALETTE = {
    "green": Fore.GREEN,
    "red": Fore.RED,
    "blue": Fore.BLUE,
    "yellow": Fore.YELLOW,
    "magenta": Fore.MAGENTA,
    "cyan": Fore.CYAN,
    "white": Fore.WHITE,
    "black": Fore.BLACK,
    "gray": Fore.LIGHTBLACK_EX,
    "orange": Fore.LIGHTRED_EX,
}


class DataStream:
    def __init__(self, lane_x, tty_height, force_bold, glyph_pool, chroma_shift, base_color):
        self.lane_x = lane_x
        self.tty_height = tty_height
        self.head_ptr = 0
        self.tail_ptr = -1
        self.tail_span = random.randint(tty_height // 4, tty_height // 2)
        self.eof = False
        self.force_bold = force_bold
        self.glyph_pool = glyph_pool
        self.chroma_shift = chroma_shift
        self.base_color = base_color

    def tick(self):
        if self.eof:
            return False

        self.head_ptr += 1
        if self.head_ptr >= self.tty_height:
            self.eof = True

        return True

    def emit_at(self, y):
        color = random.choice(list(ANSI_PALETTE.values())) if self.chroma_shift else self.base_color
        weight = Style.BRIGHT if self.force_bold else Style.NORMAL

        if y == self.head_ptr:
            return random.choice(self.glyph_pool), Fore.WHITE + weight
        elif self.tail_ptr <= y < self.head_ptr:
            return random.choice(self.glyph_pool), color + weight
        elif y == self.tail_ptr - 1:
            return ' ', Fore.BLACK

        return None, None

    def decay_tail(self):
        if self.tail_ptr < self.head_ptr:
            self.tail_ptr += 1
        return self.tail_ptr < self.tty_height


class MatrixCore:
    def __init__(self, max_streams, tick_rate, glyph_pool, force_bold, chroma_shift, color_key):
        self.max_streams = max_streams
        self.tick_rate = tick_rate
        self.force_bold = force_bold
        self.glyph_pool = glyph_pool
        self.chroma_shift = chroma_shift
        self.base_color = ANSI_PALETTE.get(color_key, Fore.GREEN)
        self.streams = []
        self.tty_width, self.tty_height = self.probe_tty()

    def probe_tty(self):
        return shutil.get_terminal_size()

    def spawn_stream(self):
        if len(self.streams) < self.max_streams:
            lane = random.randint(0, self.tty_width - 1)
            if all(stream.lane_x != lane for stream in self.streams):
                self.streams.append(
                    DataStream(
                        lane,
                        self.tty_height,
                        self.force_bold,
                        self.glyph_pool,
                        self.chroma_shift,
                        self.base_color,
                    )
                )

    def advance_streams(self):
        for stream in self.streams[:]:
            if not stream.tick() and not stream.decay_tail():
                self.streams.remove(stream)

    def render_frame(self):
        framebuffer = [[' ' for _ in range(self.tty_width)] for _ in range(self.tty_height)]
        colorbuffer = [['' for _ in range(self.tty_width)] for _ in range(self.tty_height)]

        for stream in self.streams:
            for y in range(self.tty_height):
                glyph, color = stream.emit_at(y)
                if glyph:
                    framebuffer[y][stream.lane_x] = glyph
                    colorbuffer[y][stream.lane_x] = color

        print('\033c', end='')
        for y in range(self.tty_height):
            scanline = ''.join(colorbuffer[y][x] + framebuffer[y][x] for x in range(self.tty_width))
            print(scanline)

    def boot(self):
        try:
            while True:
                w, h = self.probe_tty()

                if w != self.tty_width or h != self.tty_height:
                    self.tty_width, self.tty_height = w, h
                    self.streams.clear()

                self.spawn_stream()
                self.advance_streams()
                self.render_frame()
                time.sleep(self.tick_rate)
        except KeyboardInterrupt:
            print('\033c', end='')


def parse_flags():
    parser = argparse.ArgumentParser(description="Matrix-style terminal animation.")
    parser.add_argument("-b", action="store_true", help="Force bold glyphs")
    parser.add_argument("-V", action="store_true", help="Print version and exit")
    parser.add_argument("-u", type=int, choices=range(0, 11), default=4, help="Tick rate (0–10)")
    parser.add_argument("-C", type=str, choices=list(ANSI_PALETTE.keys()), default="green", help="Base color")
    parser.add_argument("-r", action="store_true", help="Enable chroma shift (rainbow mode)")
    return parser.parse_args()


if __name__ == "__main__":
    flags = parse_flags()

    if flags.V:
        print("Matrix Core v1.0")
        raise SystemExit

    GLYPH_POOL = list(string.printable[:-6])

    kernel = MatrixCore(
        max_streams=20,
        tick_rate=flags.u / 40,
        glyph_pool=GLYPH_POOL,
        force_bold=flags.b,
        chroma_shift=flags.r,
        color_key=flags.C,
    )

    kernel.boot()
