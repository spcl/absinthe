# Copyright (c) 2019, ETH Zurich

""" this module analyzes the stencil program data dependencies """

from re import findall
from itertools import groupby

def compute_bounds(values):
    """
    return bounding box for list of offsets
    """
    i = [value[0] for value in values]
    j = [value[1] for value in values]
    k = [value[2] for value in values]
    bounds = lambda offsets: (min(offsets), max(offsets))
    return (bounds(i), bounds(j), bounds(k))

def sum_box(box1, box2):
    """
    return the sum of two bounding boxes
    """
    return tuple(tuple(sum(offs) for offs in zip(dim[0], dim[1])) for dim in zip(box1, box2))

def max_box(box1, box2):
    """
    return the maximum of two bounding boxes
    """
    ext = lambda values: min(values) if sum(values) <= 0 else max(values)
    return tuple(tuple(ext(offs) for offs in zip(dim[0], dim[1])) for dim in zip(box1, box2))

def min_box(box1, box2):
    """
    return the minimum of two bounding boxes
    """
    ext = lambda values: max(values) if sum(values) <= 0 else min(values)
    return tuple(tuple(ext(offs) for offs in zip(dim[0], dim[1])) for dim in zip(box1, box2))

def check_widths(accesses, program):
    """
    return true if an access is out of bounds
    """
    for _, box in accesses.items():
        if max([abs(x) for x in box[0]]) > program["HX"]:
            return False
        if max([abs(y) for y in box[1]]) > program["HY"]:
            return False
        if max([abs(z) for z in box[2]]) > program["HZ"]:
            return False
    return True

def compute_halo(remote, local):
    """
    return compute halo for given remote and local bounding boxes
    """
    inner = min_box(remote, local)
    halo = {"OX" : remote[0], "IX" : inner[0],
            "OY" : remote[1], "IY" : inner[1],
            "OZ" : remote[2], "IZ" : inner[2]}
    return halo

def not_empty(halo):
    """
    return true if the halo is not empty
    """
    outer = [halo["OX"], halo["OY"], halo["OZ"]]
    inner = [halo["IX"], halo["IY"], halo["IZ"]]
    empty = lambda x: x[0][0] - x[1][0] >= 0 and x[0][1] - x[1][1] <= 0
    empty = [empty(value) for value in zip(outer, inner)]
    return False in empty

def parse_stencil(stencil):
    """
    return offset map
    """
    matches = findall(
        r"(\w+)\("                      # match the array name
        r"\s*i+(\s*[+-]+\s*\d)?\s*,"    # match the i offset
        r"\s*j+(\s*[+-]+\s*\d)?\s*,"    # match the j offset
        r"\s*k+(\s*[+-]+\s*\d)?\s*\)",  # match the k offset
        stencil)
    convert = lambda x: 0 if x == "" else int(x)
    parse = lambda x: (x[0], (convert(x[1]), convert(x[2]), convert(x[3])))
    groups = groupby(sorted(list(map(parse, matches))), lambda x: x[0])
    offsets = dict([(key, [offset[1] for offset in offsets]) for key, offsets in groups])
    return offsets

# analyze the stencil access pattern
def analyze_stencil(stencil):
    """
    return the stencil access offsets
    for example:
    {'wgt': ((0, 0), (0, 0), (0, 0)),
    'fli': ((-1, 0), (0, 0), (0, 0)),
    'flj': ((0, 0), (-1, 0), (0, 0))}
    """
    offsets = parse_stencil(stencil)
    accesses = dict([(key, compute_bounds(values)) for key, values in offsets.items()])
    return accesses

# count number of operand fetches
def count_fetches(stencil):
    """
    return number of operands fetched by the stencil
    """
    offsets = parse_stencil(stencil)
    count = 1 # 1x write access per stencil
    for _, value in offsets.items():
        count = count + len(set(value))
    return count

# analyze the stencil access offsets
def analyze_offsets(program):
    """
    return the access offsets of all stencil accesses
    """
    for group0 in program["TILING"]["GROUPS"]:
        for group1 in group0["GROUPS"]:
            stencils = []
            for stencil in group1["STENCILS"]:
                stencils.append({
                    "NAME": stencil,
                    "OFFSETS": analyze_stencil(program["STENCILS"][stencil]),
                    "LAMBDA": program["STENCILS"][stencil]
                })
            group1["STENCILS"] = stencils

# analyze the necessary amount of redundant computation
def analyze_boundary(program, group, stencils, dependencies):
    """
    return the updated dependencies
    """
    accesses = {}
    # initialize the output accesses to zero
    for output in group["OUTPUTS"]:
        accesses[output] = ((0, 0), (0, 0), (0, 0))
    # analyze the amount of redundant computations
    for stencil, offsets in reversed(stencils):
        for name, offset in offsets.items():
            if name in accesses:
                accesses[name] = max_box(accesses[name], sum_box(offset, accesses[stencil]))
            else:
                accesses[name] = sum_box(offset, accesses[stencil])
    # verify all accesses
    assert check_widths(accesses, program), "accesses too wide"
    # compute loop and halo boundaries
    group["LOOPS"] = dict([(name, accesses[name]) for name, _ in stencils])
    group["HALOS"] = dict([(name, compute_halo(dependencies[name], accesses[name]))
                           for name in group["OUTPUTS"]
                           if not_empty(compute_halo(dependencies[name], accesses[name]))])
    # compute the output dependencies
    for name in group["INPUTS"]:
        if name in dependencies:
            dependencies[name] = max_box(dependencies[name], accesses[name])
        else:
            dependencies[name] = accesses[name]
    return dependencies

# compute the boundaries of the program
def compute_boundaries(program):
    """
    compute the program boundary widths
    """
    # compute input and output sets
    dependencies0 = dict([(name, ((0, 0), (0, 0), (0, 0))) for name in program["OUTPUTS"]])
    for group0 in reversed(program["TILING"]["GROUPS"]):
        dependencies1 = dict([(name, ((0, 0), (0, 0), (0, 0))) for name in group0["OUTPUTS"]])
        stencils0 = []
        for group1 in reversed(group0["GROUPS"]):
            # compute the group1 boundaries
            stencils1 = [(stencil["NAME"], stencil["OFFSETS"]) for stencil in group1["STENCILS"]]
            dependencies1 = analyze_boundary(program, group1, stencils1, dependencies1)
            stencils0 = stencils1 + stencils0
        # compute the group0 boundaries
        dependencies0 = analyze_boundary(program, group0, stencils0, dependencies0)
    # add a dummy group at the beginning of the program
    dummy = {
        "TEMPS" : [], "INPUTS" : [], "OUTPUTS" : [], "GROUPS" : [], "LOOPS" : {},
        "HALOS" : dict([(name, compute_halo(dependencies0[name], ((0, 0), (0, 0), (0, 0))))
                        for name in program["TILING"]["INPUTS"]
                        if not_empty(compute_halo(dependencies0[name], ((0, 0), (0, 0), (0, 0))))])
    }
    program["TILING"]["GROUPS"] = [dummy] + program["TILING"]["GROUPS"]
    # number the groups using an identifier
    identifier0 = 0
    identifier1 = 0
    for group0 in program["TILING"]["GROUPS"]:
        group0["ID"] = identifier0
        identifier0 = identifier0 + 1
        for group1 in group0["GROUPS"]:
            group1["ID"] = identifier1
            identifier1 = identifier1 + 1

# compute the group data flow
def analyze_dataflow(group, dataflow, dependencies):
    """
    return the updated dependency set
    """
    local = set([])
    outputs = set([])
    temps = set([])
    for reads, writes in reversed(dataflow):
        local = local.union(reads)
        for read in writes:
            if read in dependencies:
                outputs.add(read)
            else:
                temps.add(read)
    # compute the inputs
    inputs = local.difference(outputs).difference(temps)
    group["OUTPUTS"] = list(outputs)
    group["INPUTS"] = list(inputs)
    group["TEMPS"] = list(temps)
    return dependencies.union(inputs)

# compute the data flow of the stencil program
def compute_dataflow(program):
    """
    compute the program data flow
    """
    # compute the stencil accesses
    analyze_offsets(program)
    # compute input and output sets
    dependencies = set(program["OUTPUTS"])
    dependencies0 = dependencies.copy()
    for group0 in reversed(program["TILING"]["GROUPS"]):
        dependencies1 = dependencies0.copy()
        for group1 in reversed(group0["GROUPS"]):
            # perform the group1 dependency update
            dataflow1 = [([read for read, _ in stencil["OFFSETS"].items()], [stencil["NAME"]])
                         for stencil in group1["STENCILS"]]
            dependencies1 = analyze_dataflow(group1, dataflow1, dependencies1)
        # perform the group0 dependency update
        dataflow0 = [(group["INPUTS"], group["OUTPUTS"]) for group in group0["GROUPS"]]
        dependencies0 = analyze_dataflow(group0, dataflow0, dependencies0)
    # perform program dependency update
    dataflow = [(group["INPUTS"], group["OUTPUTS"]) for group in program["TILING"]["GROUPS"]]
    analyze_dataflow(program["TILING"], dataflow, set(program["OUTPUTS"]))

# verify verify_program
def verify_program(program):
    """
    verify that code generation is possible
    """
    # compute subdomain sizes
    xsize0 = (program["X"] + program["TILING"]["NX"] - 1) // program["TILING"]["NX"]
    ysize0 = (program["Y"] + program["TILING"]["NY"] - 1) // program["TILING"]["NY"]
    zsize0 = (program["Z"] + program["TILING"]["NZ"] - 1) // program["TILING"]["NZ"]
    assert xsize0 > 0, "x size not large enough for domain decomposition"
    assert ysize0 > 0, "y size not large enough for domain decomposition"
    assert zsize0 > 0, "z size not large enough for domain decomposition"
    # make sure the subdomains are large enough for cache tiles
    for group0 in program["TILING"]["GROUPS"]:
        for group1 in group0["GROUPS"]:
            xsize1 = (xsize0 + group1["NX"] - 1) // group1["NX"]
            ysize1 = (ysize0 + group1["NY"] - 1) // group1["NY"]
            zsize1 = (zsize0 + group1["NZ"] - 1) // group1["NZ"]
            assert xsize1 > 0, "x size not large enough for cache tiling"
            assert ysize1 > 0, "y size not large enough for cache tiling"
            assert zsize1 > 0, "z size not large enough for cache tiling"
