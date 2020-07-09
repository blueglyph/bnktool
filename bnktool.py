#!/bin/env python

"""
Adlib Instrument Bank file tool.
Only processes *.wem audio files.

When providing a list of names to extract/remove/update, you may use [filename] to get those names from a file.

ex:
    bnktool.py sb.bnk -l
    bnktool.py AMB_GenericVillage.bnk -u [list.txt]
"""

import argparse
from array import array
from collections import namedtuple, OrderedDict
from os import rename
from os.path import exists, splitext
from struct import pack, unpack


AudioItem = namedtuple('AudioItem', ('len', 'data'))


class InstrumentBank(object):

    MAGIC_DIDX  = 0x58444944
    MAGIC_AUDIO = 0x41544144

    def __init__(self, bnk_file, verbose=False):
        self.file = bnk_file
        self.audio_items = OrderedDict()
        self.header = []
        self.trailing_data = b''
        self.dirty = False
        self.verbose = verbose
        self._parse()

    def _parse(self):
        """Parses the Bank file and extracts the audio data."""
        with open(self.file, 'rb') as file:
            # Header Info: magicNumber, headerLength, version, soundbankid
            self.header.extend(unpack('<IIII', file.read(16)))
            current_pos = 16
            while current_pos < self.header[1] + 8:
                self.header.extend(unpack('<I', file.read(4)))  # Unknown
                current_pos += 4

            # DIDX Header and data
            magic, length = unpack('<II', file.read(8))  # magicNumber, chunkLength
            if magic != self.MAGIC_DIDX:
                raise ValueError(f'AUDIO magic number expected ({self.MAGIC_DIDX:08X}), got {magic:08X} instead')
            num_items = length // 12
            if self.verbose:
                print(f'Adlib Instrument Bank version {self.header[2]}')
            audio_length = 0
            for _ in range(num_items):
                id, offset, length = unpack('<III', file.read(12))
                audio = AudioItem(len=length, data=array('b'))
                self.audio_items[str(id)] = audio
                audio_length += audio.len

            # Audio chunk header and data
            magic, length = unpack('<II', file.read(8))  # magicNumber, chunkLength
            if magic != self.MAGIC_AUDIO:
                raise ValueError(f'AUDIO magic number expected ({self.MAGIC_AUDIO:08X}), got {magic:08X} instead')
            padding = 0
            for audio in self.audio_items.values():
                file.read(padding)
                audio.data.fromfile(file, audio.len)
                # Align on 16-byte boundary for start of all items
                padding = -audio.len % 16

            # Trailing (unprocessed) data
            self.trailing_data = file.read()

    def extract(self, files=None):
        """Extracts audio files corresponding to the names given in <files>. By default, extracts all the files."""
        if files is None or len(files) == 0:
            files = (f"{id}.wem" for id in self.audio_items)
        for file in files:
            id, ext = splitext(file)
            print(f'.. extracting {id}.wem')
            audio = self.audio_items[id]
            with open(f'{id}.wem', 'wb') as f:
                audio.data.tofile(f)

    def to_file(self, filename):
        """Writes the content to a .bnk Bank file"""
        with open(filename, 'wb') as outfile:
            # Header
            outfile.writelines(pack('<I', i) for i in self.header)

            # DIDX
            outfile.write(pack('<II', self.MAGIC_DIDX, len(self.audio_items) * 12))
            offset = 0
            for id, audio in self.audio_items.items():
                outfile.write(pack('<III', int(id), offset, audio.len))
                padding = -audio.len % 16
                offset += audio.len + padding

            # Audio
            length = sum((audio.len + 15) & ~15 for audio in self.audio_items.values()) - padding
            outfile.write(pack('<II', self.MAGIC_AUDIO, length))
            padding = 0
            for audio in self.audio_items.values():
                outfile.write(b'\x00' * padding)
                audio.data.tofile(outfile)
                padding = -audio.len % 16

            # Footer
            outfile.write(self.trailing_data)

    def print_list(self):
        """Prints the content info"""
        if self.verbose:
            print(f"{len(self.audio_items)} audio items")
        for id, audio in self.audio_items.items():
            if self.verbose:
                print(f'{id}.wem : {audio.len} bytes')
            else:
                print(f'{id}.wem')

    def update(self, to_update=None):
        """Updates the content with audio files"""
        for file in to_update:
            print(f'.. updating {file}')
            id, ext = splitext(file)
            with open(file, 'rb') as f:
                data = array('b', f.read())
            self.audio_items[id] = AudioItem(len=len(data), data=data)
            self.dirty = True

    def empty(self, to_remove=None):
        """Replaces selected content with zero-length data"""
        remove_list = to_remove or []
        for name in remove_list:
            id, ext = splitext(name)
            print(f'.. emptying {id}{ext}')
            self.audio_items[id] = AudioItem(0, array('b'))
            self.dirty = True

    def close(self):
        """In case of change (dirty flag), saves a backup and update the Soundbank file"""
        if self.dirty:
            i = 0
            while exists(f'{self.file}.{i:03d}'):
                i += 1
            rename(self.file, f'{self.file}.{i:03d}')
            self.to_file(self.file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def names_from_file(filename):
    """Takes filenames from the content of a file (removes spaces and end-of-lines, no comment allowed)"""
    with open(filename) as f:
        item_list = [name for name in f.read().split() if name]
    return item_list

def expand_item_list(items):
    """Expands the item list with names read from a file, for each item between []."""
    result = []
    for i in items:
        if i.startswith('[') and i.endswith(']'):
            result.extend(names_from_file(i[1:-1]))
        else:
            result.append(i)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('bank', type=str,
                        help='bank file to process (*.bnk)')
    parser.add_argument('--list', '-l', action='store_true',
                        help='list files contained in the bank')
    parser.add_argument('--extract', '-x', nargs='*', type=str,
                        help='extract one or several files (no argument = extract all)')
    parser.add_argument('--update', '-u', nargs='+', type=str,
                        help='update one or several files')
    parser.add_argument('--empty', '-e', nargs='+', type=str,
                        help='remove one or several files by replacing them with empty content')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='verbose output')
    args = parser.parse_args()

    with InstrumentBank(args.bank, verbose=args.verbose) as bank:
        if args.list:
            bank.print_list()
        if args.extract is not None:
            bank.extract(expand_item_list(args.extract))
        if args.update:
            bank.update(expand_item_list(args.update))
        if args.empty:
            bank.empty(expand_item_list(args.empty))
