#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 - cologler <skyoflw@gmail.com>
# ----------
# 
# ----------

import io

class FormatError(Exception):
    pass

_BYTE_ORDER = 'little'

class Header:
    def __init__(self):
        # uint32_t magic;               Always PSF
        # uint32_t version;             Usually 1.1
        # uint32_t key_table_start;     Start offset of key_table
        # uint32_t data_table_start;    Start offset of data_table
        # uint32_t tables_entries;      Number of entries in all tables
        
        self._magic = None
        self._version = None
        self._key_table_start = None
        self._data_table_start = None
        self._tables_entries = None

    @property
    def key_table_start(self):
        return self._key_table_start

    @property
    def data_table_start(self):
        return self._data_table_start

    @property
    def tables_entries(self):
        return self._tables_entries

    def fix_data(self, sfo):
        self._tables_entries = len(sfo)
        raise NotImplementedError

    def from_reader(self, reader):
        self._magic = reader.read(4)
        self._version = reader.read(4)
        self._key_table_start = int.from_bytes(reader.read(4), _BYTE_ORDER)
        self._data_table_start = int.from_bytes(reader.read(4), _BYTE_ORDER)
        self._tables_entries = int.from_bytes(reader.read(4), _BYTE_ORDER)
        if self._magic != b'\x00PSF':
            raise FormatError
        return self

class IndexTableEntry:
    FORMAT_UTF8S = b'\x04\x00'
    '''utf8 character string, NULL terminated'''
    FORMAT_UTF8  = b'\x04\x02'
    '''
    Allways has a length of 4 bytes in len and max_len
    (even in the case some bytes are not used, all them are marked as used)
    '''
    FORMAT_INT32 = b'\x04\x04'

    def __init__(self):
        # uint16_t key_offset;      param_key offset (relative to start offset of key_table) */
        # uint16_t data_fmt;        param_data data type */
        # uint32_t data_len;        param_data used bytes */
        # uint32_t data_max_len;    param_data total bytes */
        # uint32_t data_offset;     param_data offset (relative to start offset of data_table) */
        
        self._key_offset   = None
        self._data_fmt     = None
        self._data_len     = None
        self._data_max_len = None
        self._data_offset  = None

    @property
    def key_offset(self):
        return self._key_offset

    @property
    def data_fmt(self):
        return self._data_fmt

    @property
    def data_len(self):
        return self._data_len

    @property
    def data_offset(self):
        return self._data_offset

    @property
    def data_max_len(self):
        return self._data_max_len

    def fix_data(self, data):
        raise NotImplementedError

    def from_reader(self, reader):
        self._key_offset   = int.from_bytes(reader.read(2), _BYTE_ORDER)
        self._data_fmt     = reader.read(2)
        self._data_len     = int.from_bytes(reader.read(4), _BYTE_ORDER)
        self._data_max_len = int.from_bytes(reader.read(4), _BYTE_ORDER)
        self._data_offset  = int.from_bytes(reader.read(4), _BYTE_ORDER)

        if  self._data_fmt != self.FORMAT_UTF8  and\
            self._data_fmt != self.FORMAT_INT32 and\
            self._data_fmt != self.FORMAT_UTF8S:
            print(self._data_fmt)
            raise FormatError

class Data:
    def __init__(self):
        self._index_table_entry = IndexTableEntry()
        self._key = None
        self._value = None

    @property
    def index_table_entry(self):
        return self._index_table_entry

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    def fix_data(self):
        self._index_table_entry.fix_data(self)
        raise NotImplementedError

    def __seek(self, reader, offset):
        pos = reader.tell()
        if pos != offset:
            reader.seek(offset)

    def key_from_reader(self, reader, header):
        offset = header.key_table_start + self._index_table_entry.key_offset
        self.__seek(reader, offset)
        buffer = b''
        while True:
            b = reader.read(1)
            if b == b'\x00':
                break
            buffer += b
        self._key = buffer.decode('utf8')

    def value_from_reader(self, reader, header):
        offset = header.data_table_start + self._index_table_entry.data_offset
        self.__seek(reader, offset)
        buffer = reader.read(self._index_table_entry.data_max_len)
        if self._index_table_entry.data_fmt == IndexTableEntry.FORMAT_UTF8:
            i = buffer.find(b'\x00')
            assert i >= 0
            buffer = buffer[:i]
            self._value = buffer.decode('utf8')
        elif self._index_table_entry.data_fmt == IndexTableEntry.FORMAT_INT32:
            assert len(buffer) == 4
            self._value = int.from_bytes(buffer, _BYTE_ORDER)
        else:
            raise NotImplementedError

class SfoFile:
    def __init__(self, header, data):
        assert isinstance(header, Header)
        self._header = header
        self._data = {}
        for d in data:
            self._data[d.key] = d

    def __getitem__(self, key):
        return self._data[key].value

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def _fix_data(self):
        for v in self.values():
            v.fix_data()
        self._header.fix_data(self)
        raise NotImplementedError

    @staticmethod
    def from_reader(reader):
        header = Header().from_reader(reader)
        datas = [Data() for _ in range(0, header.tables_entries)]
        for d in datas:
            d.index_table_entry.from_reader(reader)
        for d in datas:
            d.key_from_reader(reader, header)
        for d in datas:
            d.value_from_reader(reader, header)
        sfo = SfoFile(header, datas)
        return sfo

    @staticmethod
    def from_bytes(buffer):
        return SfoFile.from_reader(io.BytesIO(buffer))

def test(path):
    with open(path, mode='rb') as reader:
        sfo = SfoFile.from_reader(reader)
        for k in sfo._data:
            v = sfo._data[k]
            print('%s: "%s"' % (v._key, v._value))

if __name__ == '__main__':
    for i in range(0, 1):
        test(r'test_res\param_%s.sfo' % str(i).rjust(2, '0'))