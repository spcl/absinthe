# Copyright (c) 2019, ETH Zurich

""" this module implements the fast waves uv update """

from os import path
from sys import argv
from csv import writer
from copy import deepcopy
from getopt import getopt, GetoptError
from random import sample
from stencil_generator import generate_code, generate_makefile, build_experiment
from stencil_generator import parse_results, generate_script, write_results
from stencil_optimizer import optimize_program

# stencil program code
STENCILS = {
    "ppgk" :
        "auto res = wgtfac(i,j,k) * ppuv(i,j,k) + (1.0 - wgtfac(i,j,k)) * ppuv(i,j,k-1);",
    "ppgc" :
        "auto res = ppgk(i,j,k+1) - ppgk(i,j,k);",
    "ppgu" :
        "auto res = "
        "(ppuv(i+1,j,k) - ppuv(i,j,k)) + (ppgc(i+1,j,k) + ppgc(i,j,k)) * 0.5 * "
        "((hhl(i,j,k+1) + hhl(i,j,k)) - (hhl(i+1,j,k+1) + hhl(i+1,j,k))) / "
        "((hhl(i,j,k+1) - hhl(i,j,k)) + (hhl(i+1,j,k+1) - hhl(i+1,j,k)));",
    "ppgv" :
        "auto res = "
        "(ppuv(i,j+1,k) - ppuv(i,j,k)) + (ppgc(i,j+1,k) + ppgc(i,j,k)) * 0.5 * "
        "((hhl(i,j,k+1) + hhl(i,j,k)) - (hhl(i,j+1,k+1) + hhl(i,j+1,k))) / "
        "((hhl(i,j,k+1) - hhl(i,j,k)) + (hhl(i,j+1,k+1) - hhl(i,j+1,k)));",
    "uout" :
        "auto res = uin(i,j,k) + 0.01 * (utens(i,j,k) - ppgu(i,j,k) * "
        "(2.0 / (rho(i+1,j,k) + rho(i,j,k))));",
    "vout" :
        "auto res = vin(i,j,k) + 0.01 * (vtens(i,j,k) - ppgv(i,j,k) * "
        "(2.0 / (rho(i,j+1,k) + rho(i,j,k))));",
    "udc" :
        "auto wgt = 0.5 * (wgtfac(i,j,k) + wgtfac(i+1,j,k)); "
        "auto res = wgt * uout(i,j,k) + (1.0 - wgt) * uout(i,j,k-1);",
    "vdc" :
        "auto wgt = 0.5 * (wgtfac(i,j,k) + wgtfac(i,j+1,k)); "
        "auto res = wgt * vout(i,j,k) + (1.0 - wgt) * vout(i,j,k-1);",
    "div" :
        "auto res = "
        "0.1 * ((udc(i,j,k+1) - udc(i,j,k)) * dzdx(i,j,k) + uout(i,j,k)) + "
        "0.1 * ((udc(i-1,j,k+1) - udc(i-1,j,k)) * dzdx(i-1,j,k) - uout(i-1,j,k)) + "
        "0.2 * ((vdc(i,j,k+1) - vdc(i,j,k)) * dzdy(i,j,k) + vout(i,j,k)) + "
        "0.3 * ((vdc(i,j-1,k+1) - vdc(i,j-1,k)) * dzdy(i,j-1,k) - vout(i,j-1,k));"}

# stencil program configuration
PROGRAM = {
    "NAME" : "fastwaves",
    "CONSTANTS" : ["wgtfac", "hhl", "rho", "dzdx", "dzdy"],
    "OUTPUTS" : ["uout", "vout", "div"],
    "MACHINE" : {"CORES" : 4, "CAPACITY" : 85*1024},
    "MEMORY" : {"RW BODY" : -2.23e-7, "ST BODY": 5.71e-7, "RW PEEL" : -1.25e-6, "ST PEEL" : 5.25e-6},
    "CACHE" : {"BODY" : 9.44e-8, "PEEL" : 9.95e-7},
    "OVERLAP" : 1.0,
    "SLACK" : {"SIZE" : 0.02, "CORES" : 0.05},
    "CONSTRAINTS": {},
    "X" : 64,
    "Y" : 64,
    "Z" : 60,
    "HX" : 3,
    "HY" : 3,
    "HZ" : 3,
    "RUNS" : 64,
    "VERIFY" : False,
    "FLUSH" : True
}

# generate optimized code
def search_optimum(experiments, folder):
    """
    search the optimal implementation variant
    """
    program = deepcopy(PROGRAM)
    sequence = ["ppgk", "ppgc", "ppgu", "ppgv", "uout", "vout", "udc", "vdc", "div"]
    program["STENCILS"] = STENCILS
    program["SEQUENCE"] = sequence
    optimize_program(folder + program["NAME"], program)
    experiments[program["NAME"]] = program
    #print(program["TILING"])

# generate program variants for the auto-tuning
def auto_tune(experiments):
    """
    create auto-tuning variants
    """
    groups = [["ppgk", "ppgc", "ppgu", "ppgv", "uout", "vout"], ["udc", "vdc", "div"]]
    outputs = [["uout", "vout"], ["div"]]
    # iterate over all stencil groups
    for idx, stencils in enumerate(groups):
        # define the stencil program
        stencils = {key : value for key, value in STENCILS.items() if key in stencils}
        # search tile sizes
        for nx in [1, 2, 4, 8, 16, 32, 64]:
            for ny in [1, 2, 4, 8, 16, 32, 64]:
                for nz in [1, 2, 5, 15, 30, 60]:
                    #if nx * ny * nz >= PROGRAM["MACHINE"]["CORES"]:
                    name = PROGRAM["NAME"]
                    name = name + "-" + str(idx) + "-" + str(nx) + "-" + str(ny) + "-" + str(nz)
                    experiments[name] = deepcopy(PROGRAM)
                    experiments[name]["RUNS"] = 16
                    experiments[name]["VARIANT"] = name
                    experiments[name]["STENCILS"] = stencils
                    experiments[name]["SEQUENCE"] = groups[idx]
                    experiments[name]["OUTPUTS"] = outputs[idx]
                    # define the tiling
                    experiments[name]["TILING"] = {
                        "NX": 1, "NY": 1, "NZ": 1,
                        "GROUPS": [{
                            "GROUPS": [{
                                "STENCILS": groups[idx], "NX": nx, "NY": ny, "NZ": nz
                            }]
                        }]
                    }

# generate partly optimal codes
def explore_space(experiments, folder):
    """
    explore the space of close to optimal implementation variants
    """
    sequence = ["ppgk", "ppgc", "ppgu", "ppgv", "uout", "vout", "udc", "vdc", "div"]
    # optimal solution
    name = "OPT"
    experiments[name] = deepcopy(PROGRAM)
    experiments[name]["STENCILS"] = STENCILS
    experiments[name]["VARIANT"] = name
    experiments[name]["SEQUENCE"] = sequence
    optimize_program(folder + name, experiments[name])
    # create group constraint after the optimization
    constraints = []
    for index, group in enumerate(experiments[name]["TILING"]["GROUPS"]):
        for stencil in group["GROUPS"][0]["STENCILS"]:
            constraints.append((stencil, index))
    experiments[name]["CONSTRAINTS"]["GROUPS"] = constraints
    # hand tuned
    name = "HAND"
    experiments[name] = deepcopy(PROGRAM)
    experiments[name]["STENCILS"] = STENCILS
    experiments[name]["VARIANT"] = name
    experiments[name]["SEQUENCE"] = sequence
    experiments[name]["CONSTRAINTS"]["GROUPS"] = [("ppgk", 0), ("ppgc", 0), ("ppgu", 0),
                                                  ("ppgv", 0), ("uout", 0), ("vout", 0),
                                                  ("udc", 1), ("vdc", 1), ("div", 1)]
    experiments[name]["CONSTRAINTS"]["TILING"] = []
    for stencil in sequence:
        experiments[name]["CONSTRAINTS"]["TILING"].append(("x", stencil, -2))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("y", stencil, -9))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("z", stencil, -9))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("y", stencil, 7))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("z", stencil, 7))
    # set arbitrary high cache capacity
    experiments[name]["MACHINE"]["CAPACITY"] = 2**31
    experiments[name]["SLACK"]["SIZE"] = 1.0
    experiments[name]["SLACK"]["CORES"] = 1.0
    optimize_program(folder + name, experiments[name])
    # auto tuned
    name = "AUTO"
    experiments[name] = deepcopy(PROGRAM)
    experiments[name]["STENCILS"] = STENCILS
    experiments[name]["VARIANT"] = name
    experiments[name]["SEQUENCE"] = sequence
    experiments[name]["CONSTRAINTS"]["GROUPS"] = [("ppgk", 0), ("ppgc", 0), ("ppgu", 0),
                                                  ("ppgv", 0), ("uout", 0), ("vout", 0),
                                                  ("udc", 1), ("vdc", 1), ("div", 1)]
    experiments[name]["CONSTRAINTS"]["TILING"] = []
    for stencil in ["ppgk", "ppgc", "ppgu", "ppgv", "uout", "vout"]:
        # 1-4-5 (64x16x12)
        experiments[name]["CONSTRAINTS"]["TILING"].append(("x", stencil, -2))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("y", stencil, -5))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("y", stencil, 3))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("z", stencil, -6))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("z", stencil, 4))
    for stencil in ["udc", "vdc", "div"]:
        # 1-2-5 (64x32x12)
        experiments[name]["CONSTRAINTS"]["TILING"].append(("x", stencil, -2))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("y", stencil, -3))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("y", stencil, 1))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("z", stencil, -6))
        experiments[name]["CONSTRAINTS"]["TILING"].append(("z", stencil, 4))
    # set arbitrary high cache capacity
    experiments[name]["MACHINE"]["CAPACITY"] = 2**31
    experiments[name]["SLACK"]["SIZE"] = 1.0
    experiments[name]["SLACK"]["CORES"] = 1.0
    optimize_program(folder + name, experiments[name])
    # maximal fusion
    name = "MAX"
    experiments[name] = deepcopy(PROGRAM)
    experiments[name]["STENCILS"] = STENCILS
    experiments[name]["VARIANT"] = name
    experiments[name]["SEQUENCE"] = sequence
    experiments[name]["CONSTRAINTS"]["GROUPS"] = [(x, 0) for x in sequence]
    optimize_program(folder + name, experiments[name])
    # minimal fusion
    name = "MIN"
    experiments[name] = deepcopy(PROGRAM)
    experiments[name]["STENCILS"] = STENCILS
    experiments[name]["VARIANT"] = name
    experiments[name]["SEQUENCE"] = sequence
    experiments[name]["CONSTRAINTS"]["GROUPS"] = [(x, idx) for idx, x in enumerate(sequence)]
    optimize_program(folder + name, experiments[name])
    # compute stencil programs with different group assignments
    variants = []
    def generate_variants(current, sequence):
        """
        enumerate different group assignments
        """
        if not sequence:
            variants.append(current)
        else:
            last = current[-1][1]
            generate_variants(current + [(sequence[0], last)], sequence[1:])
            generate_variants(current + [(sequence[0], last+1)], sequence[1:])
    root = [(sequence[0], 0)]
    generate_variants(root, sequence[1:])
    # remove variants with more than 4 groups
    variants = [x for x in variants if x[-1][1] <= 4]
    # randomly filter variants
    variants = [x for x in sample(variants, 20)]
    # add the variants of the special case
    for experiment in experiments.values():
        variants.append(experiment["CONSTRAINTS"]["GROUPS"])
    exploration = {}
    # setup the experiments
    name = PROGRAM["NAME"]
    for variant in variants:
        key = name + "-" + "-".join([str(index) for _, index in variant])
        exploration[key] = deepcopy(PROGRAM)
        exploration[key]["NAME"] = key
        exploration[key]["VARIANT"] = key
        exploration[key]["STENCILS"] = STENCILS
        exploration[key]["SEQUENCE"] = sequence
        exploration[key]["CONSTRAINTS"]["GROUPS"] = variant
        optimize_program(folder + key, exploration[key])
        # generate variants with different tile counts
        groups = exploration[key]["TILING"]["GROUPS"]
        # generate variants with smaller tiles
        for dimension in ["x", "y", "z"]:
            key = name + "-" + "-".join([str(index) for _, index in variant]) + "-m" + dimension
            exploration[key] = deepcopy(PROGRAM)
            exploration[key]["NAME"] = key
            exploration[key]["VARIANT"] = key
            exploration[key]["STENCILS"] = STENCILS
            exploration[key]["SEQUENCE"] = sequence
            exploration[key]["CONSTRAINTS"]["GROUPS"] = variant
            exploration[key]["CONSTRAINTS"]["TILING"] = []
            for group in groups:
                info = group["GROUPS"][0]
                if info["N" + dimension.upper()] > 1:
                    for stencil in info["STENCILS"]:
                        constraint = (dimension, stencil, -info["N" + dimension.upper()])
                        exploration[key]["CONSTRAINTS"]["TILING"].append(constraint)
            optimize_program(folder + key, exploration[key])
        # generate variants with larger tiles
        for dimension in ["x", "y", "z"]:
            key = name + "-" + "-".join([str(index) for _, index in variant]) + "-p" + dimension
            exploration[key] = deepcopy(PROGRAM)
            exploration[key]["NAME"] = key
            exploration[key]["VARIANT"] = key
            exploration[key]["STENCILS"] = STENCILS
            exploration[key]["SEQUENCE"] = sequence
            exploration[key]["CONSTRAINTS"]["GROUPS"] = variant
            exploration[key]["CONSTRAINTS"]["TILING"] = []
            for group in groups:
                info = group["GROUPS"][0]
                if info["N" + dimension.upper()] < PROGRAM[dimension.upper()]:
                    for stencil in info["STENCILS"]:
                        constraint = (dimension, stencil, info["N" + dimension.upper()])
                        exploration[key]["CONSTRAINTS"]["TILING"].append(constraint)
            optimize_program(folder + key, exploration[key])
    # remove duplicates
    for key, program in exploration.items():
        found = False
        for existing in experiments.values():
            # if "TILING" not in existing:
            #     print("TILING not found")
            #     print(existing)
            #     print(existing["NAME"])
            # if "TILING" not in program:
            #     print("TILING not found")
            #     print(program)
            #     print(program["NAME"])
            if existing["TILING"] == program["TILING"]:
                found = True
                print("-> found existing experiment " + key)
        if not found:
            experiments[key] = program

# store the results of the code generation
def store_objectives(experiments, folder):
    """
    store the estimated performance of the implementation variants
    """
    header = ["VAR", "EST"]
    with open(folder + "estimates.csv", "w") as file:
        csv = writer(file, delimiter=",", quotechar="'", lineterminator="\n")
        csv.writerow(header)
        for _, program in experiments.items():
            csv.writerow([program["VARIANT"], str(program["OBJECTIVE"])])

# the main program
def main(arguments):
    """ main method used to run the experiments """
    optimize = False
    explore = False
    auto = False
    generate = False
    build = False
    parse = None
    folder = "./"
    try:
        short = "oeagbp:f:"
        extended = ["optimize", "explore", "auto", "generate", "build", "parse=", "folder="]
        opts, _ = getopt(arguments, short, extended)
    except GetoptError:
        print(PROGRAM["NAME"] + ".py -f <folder>")
        exit(2)
    for opt, arg in opts:
        if opt in ("-o", "--optimize"):
            optimize = True
        elif opt in ("-e", "--explore"):
            explore = True
        elif opt in ("-a", "--auto"):
            auto = True
        elif opt in ("-g", "--generate"):
            generate = True
        elif opt in ("-b", "--build"):
            build = True
        elif opt in ("-p", "--parse"):
            parse = arg
        elif opt in ("-f", "--folder"):
            folder = path.normpath(arg) + "/"
    print("-> working dir: " + str(folder))
    print("-> optimize: " + str(optimize))
    print("-> explore: " + str(explore))
    print("-> auto: " + str(auto))
    print("-> run generation: " + str(generate))
    print("-> run compilation: " + str(build))
    experiments = {}
    if explore:
        explore_space(experiments, folder)
        store_objectives(experiments, folder)
    elif optimize:
        search_optimum(experiments, folder)
    elif auto:
        auto_tune(experiments)
    # generate scripts and source code
    if generate:
        for name, program in experiments.items():
            generate_code("template_tiling.cpp", folder + name + ".cpp", program)
        generate_makefile(folder + "Makefile", experiments)
        generate_script(folder + "run.sh", experiments, PROGRAM["MACHINE"]["CORES"], 1)
    # build the code
    if build:
        for name, _ in experiments.items():
            build_experiment(folder + name)
    # parse the results
    if parse is not None:
        if auto:
            rows = parse_results(folder + parse, 0)
            write_results(rows, folder + "auto.csv")
        else:
            rows = parse_results(folder + parse)
            write_results(rows, folder + "results.csv")

if __name__ == "__main__":
    main(argv[1:])
