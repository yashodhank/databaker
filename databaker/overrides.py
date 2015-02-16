"""
Patches xypath and messytables.
"""

import re

import xypath
import messytables

import bake

class Dimension(object):

# TODO string signature: (dimself, bag, label, label item)
# TODO bag signature:    (dimself, bag, label, direction, striict)

    def __init__(self, bag, label, param1, direction=None):
        """bag: a bag - either a dimension bag or a table (in the case of a string)
           label: dimension label
           selector: either a direction+strictness for a bag or a literal string TODO
           strict: vestigal (soon)"""

        self.bag = bag
        self.strict = None
        self.string = None
        if isinstance(param1, basestring):
            self.string = param1
        else:
            self.strict = param1
        self.direction = direction  # direction
        self.bag.table.append_dimension(label, self)

    def __call__(self, cell):
        if self.string is not None:
            return self.string
        else:
            return cell.lookup(self.bag, self.direction, self.strict)

def dimension(*args, **kwargs):
    Dimension(*args, **kwargs)

xypath.Bag.dimension = dimension



# ======

class DirBag(object):
    def __init__(self, bag, direction, *args, **kwargs):
        self.bag = bag
        self.direction = direction
        self.args = args
        self.kwargs = kwargs

    def dimension(self, label):
        f = lambda cell: cell.lookup(self.bag, self.direction, *self.args, **self.kwargs)
        self.bag.table.append_dimension(label, f)

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
    (col, row) = xypath.contrib.excel.excel_address_coordinate(reference, partial=True)
    return table.get_at(col, row)
xypath.Table.excel_ref = excel_ref

def append_dimension(table, label, func):
    if getattr(table, 'headers', None) is None:
        table.headers = {}
        table.max_header = 0
        table.headernames = [None]
    if isinstance(label, basestring):
        table.max_header += 1
        number = table.max_header
        table.headernames.append(label)
    else:
        assert isinstance(label, int)
        number = label
    table.headers[number] = func
    bake.showtime("got header {}".format(label))
xypath.Table.append_dimension = append_dimension

def debug_dimensions(table):
    table.append_dimension("ref", lambda cell: xypath.contrib.excel.excel_location(cell))
    table.append_dimension("table", lambda cell: cell.table.name)

xypath.Table.debug_dimensions = debug_dimensions

# === Bag Overrides =======================================

xypath.Bag.regex = lambda self, x: self.filter(re.compile(x))

def is_date(bag):
    return bag.filter(lambda cell: bake.datematch(cell.value, silent=True))
xypath.Bag.is_date = is_date

def is_number(bag):
    return bag.filter(lambda cell: isinstance(cell.value, (int, float, long)))
xypath.Bag.is_number = is_number

def with_direction(bag, direction, *args, **kwargs):
    return DirBag(bag, direction, *args, **kwargs)
xypath.Bag.with_direction = with_direction

def group(bag, regex):
    """get the text"""
    bag.assert_one()
    match = re.search(regex, bag.value)
    if not match:
        return None
    matchtext = match.groups(0)[0]
    assert matchtext
    return matchtext
xypath.Bag.group = group

def one_of(bag, options):
    return bag.filter(lambda cell: cell.value in options)#
xypath.Bag.one_of = one_of
