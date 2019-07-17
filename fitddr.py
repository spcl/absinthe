# Copyright (c) 2019, ETH Zurich

""" module that implements test stencils to fit ddr model """

import sys
import os
import getopt
import copy
from stencil_generator import generate_code, generate_script, generate_makefile
from stencil_generator import build_experiment, write_results, parse_results

# set the core count of the target system
CORES = 4

# stencil program configuration
IN0BD0 = {
    "o0": "auto res = 0.0;",
    "o1": "auto res = o0(i,j,k);",
    "o2": "auto res = o1(i,j,k);",
    "o3": "auto res = o2(i,j,k);",
    "o4": "auto res = o3(i,j,k);",
    "o5": "auto res = o4(i,j,k);",
    "o6": "auto res = o5(i,j,k);",
    "o7": "auto res = o6(i,j,k);",
    "o8": "auto res = o7(i,j,k);"
}
IN1BD0 = {
    "o0": "auto res = i0(i,j,k);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k);"
}
IN1BD1 = {
    "o0": "auto res = i0(i,j,k) - i0(i-1,j-1,k-1) - i0(i+1,j+1,k+1);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) - i1(i-1,j-1,k-1) - i1(i+1,j+1,k+1);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) - i2(i-1,j-1,k-1) - i2(i+1,j+1,k+1);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) - i3(i-1,j-1,k-1) - i3(i+1,j+1,k+1);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) - i4(i-1,j-1,k-1) - i4(i+1,j+1,k+1);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) - i5(i-1,j-1,k-1) - i5(i+1,j+1,k+1);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) - i6(i-1,j-1,k-1) - i6(i+1,j+1,k+1);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) - i7(i-1,j-1,k-1) - i7(i+1,j+1,k+1);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) - i8(i-1,j-1,k-1) - i8(i+1,j+1,k+1);"
}
IN1BD2 = {
    "o0": "auto res = i0(i,j,k) - i0(i-1,j-1,k-1) - i0(i+1,j+1,k+1) - i0(i-2,j-2,k-2) - i0(i+2,j+2,k+2);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) - i1(i-1,j-1,k-1) - i1(i+1,j+1,k+1) - i1(i-2,j-2,k-2) - i1(i+2,j+2,k+2);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) - i2(i-1,j-1,k-1) - i2(i+1,j+1,k+1) - i2(i-2,j-2,k-2) - i2(i+2,j+2,k+2);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) - i3(i-1,j-1,k-1) - i3(i+1,j+1,k+1) - i3(i-2,j-2,k-2) - i3(i+2,j+2,k+2);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) - i4(i-1,j-1,k-1) - i4(i+1,j+1,k+1) - i4(i-2,j-2,k-2) - i4(i+2,j+2,k+2);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) - i5(i-1,j-1,k-1) - i5(i+1,j+1,k+1) - i5(i-2,j-2,k-2) - i5(i+2,j+2,k+2);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) - i6(i-1,j-1,k-1) - i6(i+1,j+1,k+1) - i6(i-2,j-2,k-2) - i6(i+2,j+2,k+2);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) - i7(i-1,j-1,k-1) - i7(i+1,j+1,k+1) - i7(i-2,j-2,k-2) - i7(i+2,j+2,k+2);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) - i8(i-1,j-1,k-1) - i8(i+1,j+1,k+1) - i8(i-2,j-2,k-2) - i8(i+2,j+2,k+2);"
}
IN2BD0 = {
    "o0": "auto res = i0(i,j,k) + j0(i,j,k);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) + j1(i,j,k);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) + j2(i,j,k);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) + j3(i,j,k);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) + j4(i,j,k);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) + j5(i,j,k);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) + j6(i,j,k);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) + j7(i,j,k);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) + j8(i,j,k);"
}
IN2BD1 = {
    "o0": "auto res = i0(i,j,k) - i0(i-1,j-1,k-1) - i0(i+1,j+1,k+1) + j0(i,j,k) - j0(i-1,j-1,k-1) - j0(i+1,j+1,k+1);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) - i1(i-1,j-1,k-1) - i1(i+1,j+1,k+1) + j1(i,j,k) - j1(i-1,j-1,k-1) - j1(i+1,j+1,k+1);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) - i2(i-1,j-1,k-1) - i2(i+1,j+1,k+1) + j2(i,j,k) - j2(i-1,j-1,k-1) - j2(i+1,j+1,k+1);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) - i3(i-1,j-1,k-1) - i3(i+1,j+1,k+1) + j3(i,j,k) - j3(i-1,j-1,k-1) - j3(i+1,j+1,k+1);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) - i4(i-1,j-1,k-1) - i4(i+1,j+1,k+1) + j4(i,j,k) - j4(i-1,j-1,k-1) - j4(i+1,j+1,k+1);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) - i5(i-1,j-1,k-1) - i5(i+1,j+1,k+1) + j5(i,j,k) - j5(i-1,j-1,k-1) - j5(i+1,j+1,k+1);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) - i6(i-1,j-1,k-1) - i6(i+1,j+1,k+1) + j6(i,j,k) - j6(i-1,j-1,k-1) - j6(i+1,j+1,k+1);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) - i7(i-1,j-1,k-1) - i7(i+1,j+1,k+1) + j7(i,j,k) - j7(i-1,j-1,k-1) - j7(i+1,j+1,k+1);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) - i8(i-1,j-1,k-1) - i8(i+1,j+1,k+1) + j8(i,j,k) - j8(i-1,j-1,k-1) - j8(i+1,j+1,k+1);"
}
IN2BD2 = {
    "o0": "auto res = i0(i,j,k) - i0(i-1,j-1,k-1) - i0(i+1,j+1,k+1) - i0(i-2,j-2,k-2) - i0(i+2,j+2,k+2) + j0(i,j,k) - j0(i-1,j-1,k-1) - j0(i+1,j+1,k+1) - j0(i-2,j-2,k-2) - j0(i+2,j+2,k+2);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) - i1(i-1,j-1,k-1) - i1(i+1,j+1,k+1) - i1(i-2,j-2,k-2) - i1(i+2,j+2,k+2) + j1(i,j,k) - j1(i-1,j-1,k-1) - j1(i+1,j+1,k+1) - j1(i-2,j-2,k-2) - j1(i+2,j+2,k+2);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) - i2(i-1,j-1,k-1) - i2(i+1,j+1,k+1) - i2(i-2,j-2,k-2) - i2(i+2,j+2,k+2) + j2(i,j,k) - j2(i-1,j-1,k-1) - j2(i+1,j+1,k+1) - j2(i-2,j-2,k-2) - j2(i+2,j+2,k+2);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) - i3(i-1,j-1,k-1) - i3(i+1,j+1,k+1) - i3(i-2,j-2,k-2) - i3(i+2,j+2,k+2) + j3(i,j,k) - j3(i-1,j-1,k-1) - j3(i+1,j+1,k+1) - j3(i-2,j-2,k-2) - j3(i+2,j+2,k+2);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) - i4(i-1,j-1,k-1) - i4(i+1,j+1,k+1) - i4(i-2,j-2,k-2) - i4(i+2,j+2,k+2) + j4(i,j,k) - j4(i-1,j-1,k-1) - j4(i+1,j+1,k+1) - j4(i-2,j-2,k-2) - j4(i+2,j+2,k+2);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) - i5(i-1,j-1,k-1) - i5(i+1,j+1,k+1) - i5(i-2,j-2,k-2) - i5(i+2,j+2,k+2) + j5(i,j,k) - j5(i-1,j-1,k-1) - j5(i+1,j+1,k+1) - j5(i-2,j-2,k-2) - j5(i+2,j+2,k+2);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) - i6(i-1,j-1,k-1) - i6(i+1,j+1,k+1) - i6(i-2,j-2,k-2) - i6(i+2,j+2,k+2) + j6(i,j,k) - j6(i-1,j-1,k-1) - j6(i+1,j+1,k+1) - j6(i-2,j-2,k-2) - j6(i+2,j+2,k+2);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) - i7(i-1,j-1,k-1) - i7(i+1,j+1,k+1) - i7(i-2,j-2,k-2) - i7(i+2,j+2,k+2) + j7(i,j,k) - j7(i-1,j-1,k-1) - j7(i+1,j+1,k+1) - j7(i-2,j-2,k-2) - j7(i+2,j+2,k+2);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) - i8(i-1,j-1,k-1) - i8(i+1,j+1,k+1) - i8(i-2,j-2,k-2) - i8(i+2,j+2,k+2) + j8(i,j,k) - j8(i-1,j-1,k-1) - j8(i+1,j+1,k+1) - j8(i-2,j-2,k-2) - j8(i+2,j+2,k+2);"
}
IN3BD0 = {
    "o0": "auto res = i0(i,j,k) + j0(i,j,k) + k0(i,j,k);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) + j1(i,j,k) + k1(i,j,k);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) + j2(i,j,k) + k2(i,j,k);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) + j3(i,j,k) + k3(i,j,k);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) + j4(i,j,k) + k4(i,j,k);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) + j5(i,j,k) + k5(i,j,k);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) + j6(i,j,k) + k6(i,j,k);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) + j7(i,j,k) + k7(i,j,k);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) + j8(i,j,k) + k88(i,j,k);"
}
IN3BD1 = {
    "o0": "auto res = i0(i,j,k) - i0(i-1,j-1,k-1) - i0(i+1,j+1,k+1) + j0(i,j,k) - j0(i-1,j-1,k-1) - j0(i+1,j+1,k+1) + k0(i,j,k) - k0(i-1,j-1,k-1) - k0(i+1,j+1,k+1);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) - i1(i-1,j-1,k-1) - i1(i+1,j+1,k+1) + j1(i,j,k) - j1(i-1,j-1,k-1) - j1(i+1,j+1,k+1) + k1(i,j,k) - k1(i-1,j-1,k-1) - k1(i+1,j+1,k+1);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) - i2(i-1,j-1,k-1) - i2(i+1,j+1,k+1) + j2(i,j,k) - j2(i-1,j-1,k-1) - j2(i+1,j+1,k+1) + k2(i,j,k) - k2(i-1,j-1,k-1) - k2(i+1,j+1,k+1);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) - i3(i-1,j-1,k-1) - i3(i+1,j+1,k+1) + j3(i,j,k) - j3(i-1,j-1,k-1) - j3(i+1,j+1,k+1) + k3(i,j,k) - k3(i-1,j-1,k-1) - k3(i+1,j+1,k+1);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) - i4(i-1,j-1,k-1) - i4(i+1,j+1,k+1) + j4(i,j,k) - j4(i-1,j-1,k-1) - j4(i+1,j+1,k+1) + k4(i,j,k) - k4(i-1,j-1,k-1) - k4(i+1,j+1,k+1);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) - i5(i-1,j-1,k-1) - i5(i+1,j+1,k+1) + j5(i,j,k) - j5(i-1,j-1,k-1) - j5(i+1,j+1,k+1) + k5(i,j,k) - k5(i-1,j-1,k-1) - k5(i+1,j+1,k+1);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) - i6(i-1,j-1,k-1) - i6(i+1,j+1,k+1) + j6(i,j,k) - j6(i-1,j-1,k-1) - j6(i+1,j+1,k+1) + k6(i,j,k) - k6(i-1,j-1,k-1) - k6(i+1,j+1,k+1);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) - i7(i-1,j-1,k-1) - i7(i+1,j+1,k+1) + j7(i,j,k) - j7(i-1,j-1,k-1) - j7(i+1,j+1,k+1) + k7(i,j,k) - k7(i-1,j-1,k-1) - k7(i+1,j+1,k+1);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) - i8(i-1,j-1,k-1) - i8(i+1,j+1,k+1) + j8(i,j,k) - j8(i-1,j-1,k-1) - j8(i+1,j+1,k+1) + k88(i,j,k) - k88(i-1,j-1,k-1) - k88(i+1,j+1,k+1);"
}
IN3BD2 = {
    "o0": "auto res = i0(i,j,k) - i0(i-1,j-1,k-1) - i0(i+1,j+1,k+1) - i0(i-2,j-2,k-2) - i0(i+2,j+2,k+2) + j0(i,j,k) - j0(i-1,j-1,k-1) - j0(i+1,j+1,k+1) - j0(i-2,j-2,k-2) - j0(i+2,j+2,k+2) + k0(i,j,k) - k0(i-1,j-1,k-1) - k0(i+1,j+1,k+1) - k0(i-2,j-2,k-2) - k0(i+2,j+2,k+2);",
    "o1": "auto res = o0(i,j,k) + i1(i,j,k) - i1(i-1,j-1,k-1) - i1(i+1,j+1,k+1) - i1(i-2,j-2,k-2) - i1(i+2,j+2,k+2) + j1(i,j,k) - j1(i-1,j-1,k-1) - j1(i+1,j+1,k+1) - j1(i-2,j-2,k-2) - j1(i+2,j+2,k+2) + k1(i,j,k) - k1(i-1,j-1,k-1) - k1(i+1,j+1,k+1) - k1(i-2,j-2,k-2) - k1(i+2,j+2,k+2);",
    "o2": "auto res = o1(i,j,k) + i2(i,j,k) - i2(i-1,j-1,k-1) - i2(i+1,j+1,k+1) - i2(i-2,j-2,k-2) - i2(i+2,j+2,k+2) + j2(i,j,k) - j2(i-1,j-1,k-1) - j2(i+1,j+1,k+1) - j2(i-2,j-2,k-2) - j2(i+2,j+2,k+2) + k2(i,j,k) - k2(i-1,j-1,k-1) - k2(i+1,j+1,k+1) - k2(i-2,j-2,k-2) - k2(i+2,j+2,k+2);",
    "o3": "auto res = o2(i,j,k) + i3(i,j,k) - i3(i-1,j-1,k-1) - i3(i+1,j+1,k+1) - i3(i-2,j-2,k-2) - i3(i+2,j+2,k+2) + j3(i,j,k) - j3(i-1,j-1,k-1) - j3(i+1,j+1,k+1) - j3(i-2,j-2,k-2) - j3(i+2,j+2,k+2) + k3(i,j,k) - k3(i-1,j-1,k-1) - k3(i+1,j+1,k+1) - k3(i-2,j-2,k-2) - k3(i+2,j+2,k+2);",
    "o4": "auto res = o3(i,j,k) + i4(i,j,k) - i4(i-1,j-1,k-1) - i4(i+1,j+1,k+1) - i4(i-2,j-2,k-2) - i4(i+2,j+2,k+2) + j4(i,j,k) - j4(i-1,j-1,k-1) - j4(i+1,j+1,k+1) - j4(i-2,j-2,k-2) - j4(i+2,j+2,k+2) + k4(i,j,k) - k4(i-1,j-1,k-1) - k4(i+1,j+1,k+1) - k4(i-2,j-2,k-2) - k4(i+2,j+2,k+2);",
    "o5": "auto res = o4(i,j,k) + i5(i,j,k) - i5(i-1,j-1,k-1) - i5(i+1,j+1,k+1) - i5(i-2,j-2,k-2) - i5(i+2,j+2,k+2) + j5(i,j,k) - j5(i-1,j-1,k-1) - j5(i+1,j+1,k+1) - j5(i-2,j-2,k-2) - j5(i+2,j+2,k+2) + k5(i,j,k) - k5(i-1,j-1,k-1) - k5(i+1,j+1,k+1) - k5(i-2,j-2,k-2) - k5(i+2,j+2,k+2);",
    "o6": "auto res = o5(i,j,k) + i6(i,j,k) - i6(i-1,j-1,k-1) - i6(i+1,j+1,k+1) - i6(i-2,j-2,k-2) - i6(i+2,j+2,k+2) + j6(i,j,k) - j6(i-1,j-1,k-1) - j6(i+1,j+1,k+1) - j6(i-2,j-2,k-2) - j6(i+2,j+2,k+2) + k6(i,j,k) - k6(i-1,j-1,k-1) - k6(i+1,j+1,k+1) - k6(i-2,j-2,k-2) - k6(i+2,j+2,k+2);",
    "o7": "auto res = o6(i,j,k) + i7(i,j,k) - i7(i-1,j-1,k-1) - i7(i+1,j+1,k+1) - i7(i-2,j-2,k-2) - i7(i+2,j+2,k+2) + j7(i,j,k) - j7(i-1,j-1,k-1) - j7(i+1,j+1,k+1) - j7(i-2,j-2,k-2) - j7(i+2,j+2,k+2) + k7(i,j,k) - k7(i-1,j-1,k-1) - k7(i+1,j+1,k+1) - k7(i-2,j-2,k-2) - k7(i+2,j+2,k+2);",
    "o8": "auto res = o7(i,j,k) + i8(i,j,k) - i8(i-1,j-1,k-1) - i8(i+1,j+1,k+1) - i8(i-2,j-2,k-2) - i8(i+2,j+2,k+2) + j8(i,j,k) - j8(i-1,j-1,k-1) - j8(i+1,j+1,k+1) - j8(i-2,j-2,k-2) - j8(i+2,j+2,k+2) + k88(i,j,k) - k88(i-1,j-1,k-1) - k88(i+1,j+1,k+1) - k88(i-2,j-2,k-2) - k88(i+2,j+2,k+2);"
}

PROGRAM = {
    "NAME" : "fitddr",
    "CONSTANTS" : ["i0", "i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8",
                   "i9", "i10", "i11", "i12", "i13", "i14", "i15", "i16", "i17",
                   "j0", "j1", "j2", "j3", "j4", "j5", "j6", "j7", "j8",
                   "j9", "j10", "j11", "j12", "j13", "j14", "j15", "j16", "j17",
                   "k0", "k1", "k2", "k3", "k4", "k5", "k6", "k7", "k88",
                   "k9", "k10", "k11", "k12", "k13", "k14", "k15", "k16", "k17"],
    "OUTPUTS" : ["o0", "o1", "o2", "o3", "o4", "o5", "o6", "o7", "o8"],
    "X" : 24,
    "Y" : 24,
    "Z" : 8,
    "HX" : 3,
    "HY" : 3,
    "HZ" : 3,
    "RUNS" : 64,
    "VERIFY" : False,
    "FLUSH" : True
}
TILING = {
    "NX" : 1, "NY" : 1, "NZ" : 1,
    "GROUPS" : [
        {
            "GROUPS" : [
                {
                    "NX" : 2, "NY" : 2, "NZ" : (5 * CORES),
                    "STENCILS" : ["o0", "o1", "o2", "o3", "o4", "o5", "o6", "o7", "o8"]
                }]
        }]
}

# the main program
def main(argv):
    """ main method used to run the experiments """
    generate = False
    build = False
    parse = None
    folder = "./"
    try:
        short = "gbvp:f:"
        extended = ["generate", "build", "verify", "parse=", "folder="]
        opts, _ = getopt.getopt(argv, short, extended)
    except getopt.GetoptError:
        print(PROGRAM["NAME"] + ".py -g -b -v -p <file> -f <folder>")
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-g", "--generate"):
            generate = True
        elif opt in ("-b", "--build"):
            build = True
        elif opt in ("-p", "--parse"):
            parse = arg
        elif opt in ("-f", "--folder"):
            folder = os.path.normpath(arg) + "/"
    print("-> working dir: " + folder)
    print("-> run generation: " + str(generate))
    print("-> run compilation: " + str(build))
    if parse is not None:
        print("-> parse file: " + folder + parse)
    # generate different configurations
    experiments = {}
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN0BD0)
                    program["VARIANT"] = str("IN0BD0")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN1BD0)
                    program["VARIANT"] = str("IN1BD0")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN2BD0)
                    program["VARIANT"] = str("IN2BD0")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN3BD0)
                    program["VARIANT"] = str("IN3BD0")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN1BD1)
                    program["VARIANT"] = str("IN1BD1")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN2BD1)
                    program["VARIANT"] = str("IN2BD1")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN3BD1)
                    program["VARIANT"] = str("IN3BD1")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN1BD2)
                    program["VARIANT"] = str("IN1BD2")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN2BD2)
                    program["VARIANT"] = str("IN2BD2")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    for xlen in [10, 20, 30, 50, 80]:
        for ylen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
            for zlen in [1, 2, 3, 5, 8, 13, 21, 34, 55]:
                total = xlen * ylen * zlen
                if total >= 500 and total <= 2000:
                    program = copy.deepcopy(PROGRAM)
                    program["X"] = 2 * xlen
                    program["Y"] = 2 * ylen
                    program["Z"] = (5 * CORES) * zlen
                    program["TILING"] = copy.deepcopy(TILING)
                    program["STENCILS"] = copy.deepcopy(IN3BD2)
                    program["VARIANT"] = str("IN3BD2")
                    domain = str(program["X"]) + "x" + str(program["Y"]) + "x" + str(program["Z"])
                    experiments[program["VARIANT"] + "-" + domain] = program
    # generate source code
    if generate:
        for name, experiment in experiments.items():
            generate_code("template_training.cpp", folder + name + ".cpp", experiment)
        # generate the run script
        generate_makefile(folder + "Makefile", experiments)
        generate_script(folder + "run.sh", experiments, CORES, 1)
    # generate the source codes
    if build:
        for name, _ in experiments.items():
            build_experiment(folder + name)
    # parse the output
    if parse is not None:
        rows = parse_results(folder + parse, 16) # skip the first 16 values to warmup caches
        write_results(rows, folder + "results.csv")

if __name__ == "__main__":
    main(sys.argv[1:])
