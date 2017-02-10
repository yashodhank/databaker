"""
Patches xypath and messytables.
"""

from __future__ import absolute_import, division
import re
import datetime
import warnings

import xypath
import messytables
import databaker.utils as utils
import six
from six.moves import range



class MatchNotFound(Exception):
    """failed to find match in bag.group"""
    pass


# === XLSCell Overrides ===================================

# disable this, and do it at the very end with the svalue(cell) function
"""
def text_date(cell):
    xls_format = cell.properties['formatting_string'].upper()
    quarter = int((cell.value.month -1 ) // 3) + 1  # TODO testme!
    print("quarter" + str(quarter))
    print([xls_format, cell.value, (cell.properties["formatting_string"])])
    if 'Q' in xls_format:
        py_format = "%Y Q{quarter}"
    elif 'D' in xls_format:
        warnings.warn("Day-of-month in date!")
        return cell.value
    elif 'M' in xls_format:
        py_format = "%b %Y"
    elif 'Y' in xls_format:
        py_format = "%Y"
    else:
        warnings.warn("Unable to parse dateformat: {} in {!r}".format(xls_format, cell))
        return cell.value
    return cell.value.strftime(py_format).format(quarter=quarter)

xypath.xypath.Table.from_messy_ = staticmethod(xypath.xypath.Table.from_messy)
def new_from_messy(messy_rowset):
    new_table = xypath.xypath.Table.from_messy_(messy_rowset)
    for cell in new_table.unordered_cells:
        if isinstance(cell.value, datetime.datetime):
            # it was originally an excel date
            cell.value = text_date(cell)
    return new_table
xypath.xypath.Table.from_messy = staticmethod(new_from_messy)
"""

# === Cell Overrides ======================================

def cell_repr(cell):
    column = xypath.contrib.excel.excel_column_label(cell.x+1)
    return "<{}{} {!r}>".format(column, cell.y+1, cell.value)
xypath.xypath._XYCell.__repr__ = cell_repr

# === TableSet Overrides ==================================

@property
def tabnames(tableset):
    return set(x.name for x in tableset.tables)
messytables.TableSet.names = tabnames

# === Table Overrides =====================================

def excel_ref(table, reference):
    if ':' not in reference:
        (col, row) = xypath.contrib.excel.excel_address_coordinate(reference, partial=True)
        return table.get_at(col, row)
    else:
        ((left, top), (right, bottom)) = xypath.contrib.excel.excel_range(reference)
        bag = xypath.Bag(table=table)
        if top is None and bottom is None:
            for col in range(left, right + 1):
                bag = bag | table.get_at(col, None)
        elif left is None and right is None:
            for row in range(top, bottom + 1):
                bag = bag | table.get_at(None, row)
        else:
            for row in range(top, bottom + 1):
                for col in range(left, right + 1):
                    bag = bag | table.get_at(col, row)
        return bag
xypath.Table.excel_ref = excel_ref


# === Bag Overrides =======================================

xypath.Bag.regex = lambda self, x: self.filter(re.compile(x))

def is_date(bag):
    return bag.filter(lambda cell: utils.datematch(cell.value, silent=True))
xypath.Bag.is_date = is_date

def is_number(bag):
    return bag.filter(lambda cell: isinstance(cell.value, (int, float, int)))
xypath.Bag.is_number = is_number
def is_not_number(bag):
    return bag.filter(lambda cell: not isinstance(cell.value, (int, float, int)))
xypath.Bag.is_not_number = is_not_number

def group(bag, regex):
    """get the text"""
    bag.assert_one()
    match = re.search(regex, bag.value)
    if not match:
        raise MatchNotFound("Can't find {!r} in {!r}".format(regex, bag.value))
    matchtext = match.groups(0)[0]
    assert matchtext
    return matchtext
xypath.Bag.group = group

def one_of(bag, options):
    output = None
    for option in options:
        if output is None:
            output = bag.filter(option)
        else:
            output = output | bag.filter(option)
    return output
xypath.Bag.one_of = one_of

def parent(bag):
    """for cell, get its top-left cell"""
    output_bag = xypath.Bag(table = bag.table)
    for cell in bag.unordered:
        row, _, col, _ = cell.properties.raw_span(always=True)
        output_bag.add(cell.table.get_at(col, row)._cell)
    return output_bag
xypath.Bag.parent = parent

def children(bag):
    """for top-left cell, get all cells it spans"""
    outputbag = xypath.Bag(table=bag.table)
    for parent in bag:
        top, bottom, left, right = parent.properties.raw_span(always=True)
        for row in range(top, bottom + 1):
            for col in range(left, right + 1):
                outputbag = outputbag | bag.table.get_at(col, row)
    return outputbag
xypath.Bag.children = children

def rich_text(bag):
    r = bag.property.rich
    return r
xypath.Bag.rich_text = rich_text

def spaceprefix(bag, count):
    """filter: cells starting with exactly count whitespace: no more, no less"""
    return bag.filter(re.compile("^\s{%s}\S" % count))
xypath.Bag.spaceprefix = spaceprefix

def is_whitespace(bag):
    """filter: cells which do not contain printable characters"""
    return bag.filter(lambda cell: not str(cell.value).strip())
xypath.Bag.is_whitespace = is_whitespace

def is_not_whitespace(bag):
    """filter: cells which do contain printable characters"""
    return bag.filter(lambda cell: str(cell.value).strip())
xypath.Bag.is_not_whitespace = is_not_whitespace

def by_index(bag, items):
    """filter: return numbered items from a bag.
       Note that this is 1-indexed!
       Items can be a list or a single number"""
    if isinstance(items, int):
        return bag.by_index([items])
    new = xypath.Bag(table=bag.table)
    for i, cell in enumerate(bag):
        if i+1 in items:
            new.add(cell._cell)
            if i+1 == max(items):
                return new
    raise xypath.XYPathError("get_nth needed {} items, but bag only contained {}.\n{!r}".format(max(items), len(bag), bag))
xypath.Bag.by_index = by_index

