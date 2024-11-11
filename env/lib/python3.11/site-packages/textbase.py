"""
textbase - A Python library to manipulate Inmagic/DBText style data files

The main utitlity class is TextBase.
It can be initialised with an open file, or a string buffer, named sourcefile.
Sourcefile is iterated over, splitting the contents into chunks.
Each chunk is parsed and added to an internal buffer list.
The internal buffer contains a dict for each record. Each entry in the dict
is keyed on the DBText record fieldname, the entry itself is a list of the values.

The TextBase object can be used as a generator to iterate over the contents,
or the Textbase object can be index-addressed like a list.

Example Usage:
--------------

import textbase
t = textbase.TextBase(somebuf)

print len(t)

for x in t[10:20]:
    print x.keys()

print t[0]


If you do not want the records parsed into Python dictionaries and just want 
to muck about with the records as text blobs, initialise like this:
  t = textbase.TextBase(somebuf, parse=False)

Please send me feedback if this is useful for you, or suggestions etc.
Author: Etienne Posthumus
Mail: ep@epoz.org
Dev started: 17 November 2004
"""

__version__ = "0.15"
__date__ = "20200922"

import io
from collections import OrderedDict
from typing import Callable, List, Union
import xlsxwriter


def parse(filename: str):
    # Files read as binary, we do explicit decoding at the boundary,
    return TextBase(io.open(filename, "rb"))


class TextBase:
    def __init__(
        self,
        sourcefile: bytes = None,
        separator=b"$",
        do_parse=True,
        keep_original=False,
        encoding="utf8",
    ) -> None:

        self.separator = separator
        self.__entries__: List[Union[str, OrderedDict[str, Union[str, List[str]]]]] = []
        self.keep_original = keep_original
        self.encoding = encoding
        self.sourcefile: bytes
        self.process: Callable[[List[str]], None]

        if isinstance(sourcefile, io.IOBase):
            self.sourcefile = sourcefile
        else:
            self.sourcefile = io.BytesIO(sourcefile)

        if do_parse:
            self.process = self.parse
        else:
            self.process = self.dont_parse

        # check for unicode Byte Order Mark (BOM)
        BOMcheck = self.sourcefile.read(3)
        if BOMcheck != b"\xef\xbb\xbf":
            self.sourcefile.seek(0)

        self.split()

    def dont_parse(self, chunk: List[str]) -> None:
        self.__entries__.append("".join(chunk))

    def parse(self, chunk: List[str]) -> None:
        last_field = ""
        datadict: OrderedDict[str, Union[str, List[str]]] = OrderedDict()

        for x in chunk:
            if x[0] == "#":  # skip comments
                continue

            # find where the first space character is
            spacepos = x.find(" ")

            # skip line if there are no spaces
            if spacepos == -1:
                continue

            # Get key value
            if x[0] != ";" and spacepos > 0:
                last_field = x[0:spacepos]
                if last_field.endswith(":"):
                    last_field = last_field[:-1]

            data: str = x[spacepos:].strip()

            if last_field in datadict.keys():
                if spacepos == 0:
                    datadict[last_field][-1] += "\n" + data
                else:
                    datadict[last_field].append(data)
            else:
                datadict[last_field] = [data]

        if self.keep_original:
            datadict["__original__"] = "".join(chunk)

        if datadict:
            self.__entries__.append(datadict)

    def split(self) -> None:
        chunk: List[str] = []

        for line in self.sourcefile:
            if line.strip() == self.separator:
                if chunk:
                    self.process(chunk)
                    chunk = []
            else:
                # this is the boundary that an actual read line gets "into" the system
                # we will do an explicit decoding here.
                chunk.append(line.decode(self.encoding))

        if chunk:
            self.process(chunk)

    def dump(self, filename_or_stream) -> None:
        if type(filename_or_stream) is str:
            filename_or_stream = io.open(filename_or_stream, "wb")
        for x in self.__entries__:
            for k, v in x.items():
                filename_or_stream.write(b"\n%s " % k.encode("utf8"))
                new_v = ["\n ".join(vv.split("\n")) for vv in v]
                tmp = "\n; ".join(new_v)
                filename_or_stream.write(tmp.encode("utf8"))
            filename_or_stream.write(b"\n$")

    def toxlsx(self, filename: str) -> None:
        # Collect all the fields used
        fields = set("ID")
        for x in self.__entries__:
            fields.update(x.keys())

        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        fields_idx = {}
        for i, field in enumerate(fields):
            worksheet.write(0, i, field)
            fields_idx[field] = i

        row = 1
        for x in self.__entries__:
            for k, v in x.items():
                col = fields_idx.get(k)
                worksheet.write(row, col, "\n".join(v))
            row += 1

        workbook.close()

    def __getitem__(self, key):
        return self.__entries__[key]

    def __iter__(self):
        return iter(self.__entries__)

    def __len__(self):
        return len(self.__entries__)
