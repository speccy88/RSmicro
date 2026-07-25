from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class BoolValue: value: bool
@dataclass(frozen=True)
class DintValue: value: int
@dataclass(frozen=True)
class RealValue: value: float
@dataclass(frozen=True)
class TimerValue: pre:int; acc:int; en:bool; tt:bool; dn:bool
@dataclass(frozen=True)
class CounterValue: pre:int; acc:int; cu:bool; cd:bool; dn:bool; ov:bool; un:bool

def binary32(value): return struct.unpack("=f", struct.pack("=f", float(value)))[0]

def normalize(value, type_name):
    if type_name == "BOOL":
        if type(value) is not bool: raise TypeError("BOOL requires bool")
        return BoolValue(value)
    if type_name == "DINT":
        if type(value) is not int or not -(2**31) <= value < 2**31: raise (TypeError if type(value) is not int else OverflowError)("DINT requires a signed 32-bit integer")
        return DintValue(value)
    if type_name == "REAL":
        if type(value) not in (int,float): raise TypeError("REAL requires int or float")
        return RealValue(binary32(value))
    raise TypeError(f"unsupported writable native type {type_name}")
