from enum import Enum

from pony.orm.dbapiprovider import StrConverter


class EnumConverter(StrConverter):
    def validate(self, val, obj=None):
        if not isinstance(val, Enum):
            raise ValueError("Must be an Enum.  Got {}".format(type(val)))
        return val

    def py2sql(self, val):
        return val.value

    def sql2py(self, value):
        return self.py_type(value)
