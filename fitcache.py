# Copyright (c) 2019, ETH Zurich

""" module that implements test stencils to fit cache model """

import sys
import os
import getopt
import copy
from stencil_generator import generate_code, generate_script, generate_makefile
from stencil_generator import build_experiment, write_results, parse_results

# set the core count of the target system
CORES = 4

# stencil program configuration
PT8 = {
    "t0": "auto res = i0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t1": "auto res = t0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t2": "auto res = t1(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t3": "auto res = t2(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t4": "auto res = t3(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t5": "auto res = t4(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t6": "auto res = t5(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t7": "auto res = t6(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);",
    "t8": "auto res = t7(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1);"
}
PT12 = {
    "t0": "auto res = i0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t1": "auto res = t0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t2": "auto res = t1(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t3": "auto res = t2(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t4": "auto res = t3(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t5": "auto res = t4(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t6": "auto res = t5(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t7": "auto res = t6(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);",
    "t8": "auto res = t7(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k);"
}
PT16 = {
    "t0": "auto res = i0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t1": "auto res = t0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t2": "auto res = t1(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t3": "auto res = t2(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t4": "auto res = t3(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t5": "auto res = t4(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t6": "auto res = t5(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t7": "auto res = t6(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);",
    "t8": "auto res = t7(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1);"
}
PT20 = {
    "t0": "auto res = i0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t1": "auto res = t0(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t2": "auto res = t1(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t3": "auto res = t2(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t4": "auto res = t3(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t5": "auto res = t4(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t6": "auto res = t5(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t7": "auto res = t6(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);",
    "t8": "auto res = t7(i,j,k) - i0(i-1,j,k) - i0(i+1,j,k) - i0(i,j-1,k) - i0(i,j+1,k) - i0(i,j,k-1) - i0(i,j,k+1) + i0(i-1,j-1,k) + i0(i+1,j+1,k) + i0(i-1,j+1,k) + i0(i+1,j-1,k) + i0(i-1,j,k-1) + i0(i+1,j,k+1) + i0(i-1,j,k+1) + i0(i+1,j,k-1) + i0(i,j-1,k-1) + i0(i,j+1,k+1) + i0(i,j-1,k+1) + i0(i,j+1,k-1);"
}

PROGRAM = {
    "NAME" : "fitcache",
    "CONSTANTS" : ["i0"],
    "OUTPUTS" : ["t8"],
    "X" : 24,
    "Y" : 24,
    "Z" : 8,
    "HX" : 3,
    "HY" : 3,
    "HZ" : 3,
    "RUNS" : 64,
    "VERIFY" : False,
    "FLUSH" : False
}
TILING = {
    "NX" : 1, "NY" : 1, "NZ" : 1,
    "GROUPS" : [
        {
            "GROUPS" : [
                {
                    "NX" : 2, "NY" : 2, "NZ" : (5 * CORES),
                    "STENCILS" : ["t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"]
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
                    program["STENCILS"] = copy.deepcopy(PT8)
                    program["VARIANT"] = str("PT8")
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
                    program["STENCILS"] = copy.deepcopy(PT12)
                    program["VARIANT"] = str("PT12")
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
                    program["STENCILS"] = copy.deepcopy(PT16)
                    program["VARIANT"] = str("PT16")
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
                    program["STENCILS"] = copy.deepcopy(PT20)
                    program["VARIANT"] = str("PT20")
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
