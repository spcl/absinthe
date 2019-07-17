# Copyright (c) 2019, ETH Zurich

""" this module generates optimized stencil program implementation variants """

import sys
from os import remove
from shutil import copyfile
from os.path import exists
from random import choice
from subprocess import Popen, PIPE
from xml.dom.minidom import parse
from math import log2, floor
from functools import reduce
from stencil_analyzer import analyze_stencil, count_fetches

# constants
SIZE_OF_VALUE = 8

def compute_dependencies(program):
    """
    compute the stencil dependencies
    """
    stencils = program["STENCILS"]
    # analyze the dependencies
    dependencies = dict([(name, analyze_stencil(stencil)) for name, stencil in stencils.items()])
    fetches = dict([(name, count_fetches(stencil)) for name, stencil in stencils.items()])
    # store the results
    program["DEPENDENCIES"] = dependencies
    program["FETCHES"] = fetches

def compute_sequence(program):
    """
    compute random stencil sequence
    """
    stencils = [name for name, _ in program["STENCILS"].items()]
    dependencies = program["DEPENDENCIES"]
    if "SEQUENCE" not in program:
        sequence = []
        while len(sequence) < len(program["STENCILS"]):
            candidates = []
            # compute candidate list
            for stencil in stencils:
                if stencil not in sequence:
                    inputs = [name for name, _ in program["DEPENDENCIES"][stencil].items()]
                    active = [x for x in inputs if (x in stencils) and (x not in sequence)]
                    if not active:
                        candidates.append(stencil)
            # select random candidate element
            sequence.append(choice(candidates))
        program["SEQUENCE"] = sequence
    # verify the sequence
    sequence = program["SEQUENCE"]
    assert len(sequence) == len(stencils), "sequence and stencil size differ"
    assert not (set(sequence) ^ set(stencils)), "sequence and stencil sets differ"
    for index, stencil in enumerate(sequence):
        for dependency, _ in dependencies[stencil].items():
            if dependency in sequence:
                assert index > sequence.index(dependency), "sequence violates dependency"
    print("-> optimizing sequence " + str(program["SEQUENCE"]))

def compute_utilization(program):
    """
    compute the maximal cache utilization for the entire group
    """
    sequence = program["SEQUENCE"]
    dependencies = program["DEPENDENCIES"]
    utilization = {}
    # compute the access sets for all stencils of the sequence
    accesses = [set(list(dependencies[x].keys()) + [x]) for x in sequence]
    # compute the utilization for every stencil
    for high, stencil in enumerate(sequence):
        utilization[stencil] = []
        for low in range(high + 1):
            utilization[stencil].append(len(reduce(set.union, accesses[low:high + 1])))
    # store the result
    program["UTILIZATION"] = utilization

def compute_domain(program):
    """
    compute an extended compute domain that is divisible by the number of cores
    """
    # compute the number of digits necessary to represent the number of tiles along all dimensions
    program["DX"] = range(max(1, floor(log2(program["X"])) + 1))
    program["DY"] = range(max(1, floor(log2(program["Y"])) + 1))
    program["DZ"] = range(max(1, floor(log2(program["Z"])) + 1))

def define_target(program):
    """
    define the cost function
    """
    # get relevant collections
    sequence = program["SEQUENCE"]
    # define the optimization function as sum of the group time and their startup cost
    print("Minimize")
    memory = 6 * (program["MEMORY"]["RW BODY"] + program["MEMORY"]["ST BODY"])
    print(" + ".join(["t%" + str(index) for index, _ in enumerate(sequence)]) + " + " +
          " + ".join([str(memory) + " n%xyz" + str(index) for index, _ in enumerate(sequence)]))

def compute_groups(sequence):
    """
    compute group index and flags
    """
    # assume increasing group indexes along the program sequence
    assert len(sequence) > 0, "empty stencil sequence"
    print(r"\ constrain the group indexes")
    print("g%0 = 0")
    for index in range(1, len(sequence)):
        print("g%" + str(index) + " - g%" + str(index - 1) + " <= 1")
        print("g%" + str(index) + " - g%" + str(index - 1) + " >= 0")
    # flags forced to one if the group indexes are not equal
    for high, _ in enumerate(sequence):
        for low in range(high):
            limit = len(sequence)
            print(str(-limit) + " g%" + str(low) + "#" + str(high) + " + " +
                  "g%" + str(high) + " - " + "g%" + str(low) + " <= 0")

def compute_memory(sequence, outputs, dependencies):
    """
    compute the memory cost
    """
    # compute the memory cost
    print(r"\ compute the memory cost")
    last = {}
    for index, stencil in enumerate(sequence):
        # count the loads
        for name in dependencies[stencil].keys():
            # find the last access
            try:
                last = sequence.index(next((x for x in reversed(sequence[:index])
                                            if x == name or name in dependencies[x].keys())))
            except StopIteration:
                last = None
            # check if the last access happens in the same group
            if last is not None:
                print("r%" + str(index) + "_" + name + " - " +
                      "g%" + str(last) + "#" + str(index) + " >= 0")
            else:
                print("r%" + str(index) + "_" + name + " = 1")
        # sum the loads
        print("r%" + str(index) + " - " +
              " - ".join(["r%" + str(index) + "_" + name
                          for name in dependencies[stencil].keys()]) + " = 0")
        # count the stores
        if stencil in outputs:
            print("w%" + str(index) + " = 1")
        else:
            last = sequence.index(next((x for x in reversed(sequence[index + 1:])
                                        if stencil in dependencies[x].keys())))
            # check if the last access happens in the same group
            print("w%" + str(index) + " - g%" + str(index) + "#" + str(last) + " >= 0")
        # set the read or write flag
        limit = len(dependencies[stencil].keys()) + 1
        print(str(limit) + " rw%" + str(index) + " - r%" + str(index) + " - w%" + str(index) + " >= 0")
        # set the number of streams
        print("s%" + str(index) + " - r%" + str(index) + " - w%" + str(index) + " >= 0")

def compute_boundaries(sequence, dependencies, halos):
    """
    compute the evaluation and access boundaries
    """
    # constrain the evaluation domain
    def constrain_evaluation(index, access, direction, offset, halo):
        """
        compute the evaluation domain
        """
        print("e%" + direction + str(access) + " - e%" + direction + str(index) + " + " +
              str(halo) + " g%" + str(index) + " - " + str(halo) + " g%" + str(access) + " >= " +
              str(abs(offset)))
    print(r"\ compute the evaluation domains")
    for stencil, accesses in dependencies.items():
        for (name, offsets) in accesses.items():
            if name in sequence:
                index = sequence.index(stencil)
                access = sequence.index(name)
                constrain_evaluation(index, access, "xm", offsets[0][0], halos[0])
                constrain_evaluation(index, access, "xp", offsets[0][1], halos[0])
                constrain_evaluation(index, access, "ym", offsets[1][0], halos[1])
                constrain_evaluation(index, access, "yp", offsets[1][1], halos[1])
                constrain_evaluation(index, access, "zm", offsets[2][0], halos[2])
                constrain_evaluation(index, access, "zp", offsets[2][1], halos[2])
    # compute the evaluation boundary
    def sum_evaluation(index, dimension):
        """
        count the boundary fetches
        """
        print("e%" + dimension + str(index) + " - " +
              "e%" + dimension + "m" + str(index) + " - " +
              "e%" + dimension + "p" + str(index) + " = 0")
    for index, stencil in enumerate(sequence):
        sum_evaluation(index, "x")
        sum_evaluation(index, "y")
        sum_evaluation(index, "z")
    # constrain the access boundaries
    def constrain_access(index, name, direction, offset, halo):
        """
        count the boundary accesses
        """
        # do not consider access of temporaries produced within the group
        if name in sequence:
            print("a%" + direction + str(index) + "_" + name + " - " +
                  "e%" + direction + str(index) + " - " +
                  str(halo) + " g%" + str(sequence.index(name)) + "#" + str(index) +
                  " >= " + str(abs(offset) - halo))
        else:
            print("a%" + direction + str(index) + "_" + name + " - " +
                  "e%" + direction + str(index) +
                  " >= " + str(abs(offset)))
    print(r"\ compute the access boundaries")
    for stencil, accesses in dependencies.items():
        for name, offsets in accesses.items():
            index = sequence.index(stencil)
            constrain_access(index, name, "xm", offsets[0][0], halos[0])
            constrain_access(index, name, "xp", offsets[0][1], halos[0])
            constrain_access(index, name, "ym", offsets[1][0], halos[1])
            constrain_access(index, name, "yp", offsets[1][1], halos[1])
            constrain_access(index, name, "zm", offsets[2][0], halos[2])
            constrain_access(index, name, "zp", offsets[2][1], halos[2])
    # compute the boundary reads
    def constrain_reads(stencil, index, direction, halo):
        """
        constrain the boundary reads
        """
        # compute the boundary loads
        for name in dependencies[stencil].keys():
            # compute the memory operations
            try:
                last = sequence.index(next((x for x in reversed(sequence[:index])
                                            if name in dependencies[x].keys())))
            except StopIteration:
                last = None
            if last is None:
                # fill the entire cache if there is no predecessor
                print("r%" + direction + str(index) + "_" + name + " - " +
                      "a%" + direction + str(index) + "_" + name + " = 0")
            else:
                # fill the entire cache if the predecessor is not in the group
                print("r%" + direction + str(index) + "_" + name + " - " +
                      "a%" + direction + str(index) + "_" + name + " - " +
                      str(halo) + " g%" + str(last) + "#" + str(index) + " >= " + str(-halo))
                # fill the difference with respect to the predecessor of the same group
                print("a%" + direction + str(index) + "_" + name + " - " +
                      "a%" + direction + str(last) + "_" + name + " + " +
                      str(halo) + " g%" + str(index) + " - " +
                      str(halo) + " g%" + str(last) + " >= 0")
                print("r%" + direction + str(index) + "_" + name + " - " +
                      "a%" + direction + str(index) + "_" + name + " + " +
                      "a%" + direction + str(last) + "_" + name + " + " +
                      str(halo) + " g%" + str(index) + " - " +
                      str(halo) + " g%" + str(last) + " >= 0")
    print(r"\ compute the boundary accesses")
    for index, stencil in enumerate(sequence):
        constrain_reads(stencil, index, "xm", halos[0])
        constrain_reads(stencil, index, "xp", halos[0])
        constrain_reads(stencil, index, "ym", halos[1])
        constrain_reads(stencil, index, "yp", halos[1])
        constrain_reads(stencil, index, "zm", halos[2])
        constrain_reads(stencil, index, "zp", halos[2])
    # sum the boundary reads
    def sum_reads(stencil, index, dimension):
        """
        sum the boundary reads
        """
        print("r%" + dimension + str(index) + " - " +
              " - ".join(["r%" + dimension + "m" + str(index) + "_" + name
                          for name in dependencies[stencil].keys()]) + " - " +
              " - ".join(["r%" + dimension + "p" + str(index) + "_" + name
                          for name in dependencies[stencil].keys()]) + " = 0")
    for index, stencil in enumerate(sequence):
        sum_reads(stencil, index, "x")
        sum_reads(stencil, index, "y")
        sum_reads(stencil, index, "z")

def compute_tiles(sequence, cores, sizes, digits, slack):
    """
    constrain the tile sizes
    """
    # compute the number of tiles given the binary representation
    def sum_count(dimension, index, digits):
        """
        sum the number of tiles
        """
        prefix = "n%" + dimension + str(index)
        terms = " - ".join([str(2**x) + " " + prefix + "_" + str(x) for x in digits])
        print(prefix + " - " + terms + " = 0")
    print(r"\ constrain the tile count per dimension")
    for index, _ in enumerate(sequence):
        sum_count("x", index, digits[0])
        sum_count("y", index, digits[1])
        sum_count("z", index, digits[2])
    # make sure we have at least one tile and at most size tiles
    def constrain_count(dimension, index, size):
        """
        constrain the tile counts
        """
        print("n%" + dimension + str(index) + " >= 1")
        print("n%" + dimension + str(index) + " <= " + str(size))
    for index, _ in enumerate(sequence):
        constrain_count("x", index, sizes[0])
        constrain_count("y", index, sizes[1])
        constrain_count("z", index, sizes[2])
    # compute total number of tiles
    def multiply_counts(result, dimension, index, digits, limit):
        """
        multiply the tile counts
        """
        for digit in digits:
            res = "n%" + result + dimension + str(index) + "_" + str(digit)
            val = "n%" + result + str(index)
            mul = "n%" + dimension + str(index) + "_" + str(digit)
            print(res + " - " + str(limit) + " " + mul + " <= 0")
            print(res + " - " + val + " <= 0")
            print(res + " - " + val + " - " + str(limit) + " " + mul + " >= " + str(-limit))
    print(r"\ compute the total tile count")
    for index, _ in enumerate(sequence):
        multiply_counts("x", "y", index, digits[1], sizes[0])
        multiply_counts("xy", "z", index, digits[2], sizes[0] * sizes[1])
        sum_count("xy", index, digits[1])
        sum_count("xyz", index, digits[2])
    # multiply the tile sizes with the number of tiles to get the domain size
    def multiply_sizes(dimension, index, digits, limit):
        """
        multiply the tile size
        """
        for digit in digits:
            res = "d%" + dimension + str(index) + "_" + str(digit)
            val = "y%" + dimension + str(index)
            mul = "n%" + dimension + str(index) + "_" + str(digit)
            print(res + " - " + str(limit) + " " + mul + " <= 0")
            print(res + " - " + val + " <= 0")
            print(res + " - " + val + " - " + str(limit) + " " + mul + " >= " + str(-limit))
    def sum_sizes(dimension, index, digits):
        """
        sum the domain sizes
        """
        prefix = "d%" + dimension + str(index)
        terms = " - ".join([str(2**x) + " " + prefix + "_" + str(x) for x in digits])
        print(prefix + " - " + terms + " = 0")
    print(r"\ compute the domain sizes as the product of tile count and size")
    for index, _ in enumerate(sequence):
        multiply_sizes("x", index, digits[0], sizes[0])
        multiply_sizes("y", index, digits[1], sizes[1])
        multiply_sizes("z", index, digits[2], sizes[2])
        sum_sizes("x", index, digits[0])
        sum_sizes("y", index, digits[1])
        sum_sizes("z", index, digits[2])
    # make sure the domain sizes correspond to the given sizes
    def constrain_size(dimension, index, size):
        """
        introduce tile size constraints
        """
        print("d%" + dimension + str(index) + " >= " + str(size))
        print(str(1.0 - slack["SIZE"]) + " d%" + dimension + str(index) + " <= " + str(size))
    print(r"\ constrain the domain size using the 'SIZE' slack parameter")
    for index, _ in enumerate(sequence):
        constrain_size("x", index, sizes[0])
        constrain_size("y", index, sizes[1])
        constrain_size("z", index, sizes[2])
    # make sure all cores are used in the first place
    print(r"\ constrain the tile count using the 'CORE' slack parameter")
    for index, _ in enumerate(sequence):
        print("n%xyz" + str(index) + " >= " + str(cores))
    # make sure most of the cores are used
    for index, _ in enumerate(sequence):
        # limit the number of unused tile slots
        minimum = (1.0 - slack["CORES"]) * cores
        print(str(minimum) + " x%" + str(index) + " - " + "n%xyz" + str(index) + " <= 0")
        print(str(cores) + " x%" + str(index) + " - n%xyz" + str(index) + " >= 0")
    # enforce tile count equality for stencils in the same group
    def enforce_equality(dimension, low, high, digits):
        """
        enforce tile count equality
        """
        for digit in digits:
            print("n%" + dimension + str(high) + "_" + str(digit) + " - " +
                  "n%" + dimension + str(low) + "_" + str(digit) + " + " +
                  "g%" + str(high) + " - g%" + str(low) + " >= 0")
            print("n%" + dimension + str(high) + "_" + str(digit) + " - " +
                  "n%" + dimension + str(low) + "_" + str(digit) + " + " +
                  "g%" + str(low) + " - g%" + str(high) + " <= 0")
    indexes = range(len(sequence))
    print(r"\ enforce tile size equality")
    for low, high in zip(indexes[:-1], indexes[1:]):
        enforce_equality("x", low, high, digits[0])
        enforce_equality("y", low, high, digits[1])
        enforce_equality("z", low, high, digits[2])

def compute_footprint(sequence, utilization):
    """
    compute the cache footprint
    """
    # compute the buffer utilization per stencil
    print(r"\ compute the cache footprint of the individual stencils")
    for high, stencil in enumerate(sequence):
        print("f%" + str(high) + " >= " + str(utilization[stencil][high]))
        for low in range(high):
            print("f%" + str(high) + " + " +
                  str(utilization[stencil][low]) + " g%" + str(high) + " - " +
                  str(utilization[stencil][low]) + " g%" + str(low) +
                  " >= " + str(utilization[stencil][low]))

def constrain_footprint(sequence, sizes, capacity):
    """
    constrain the cache footprint
    """
    # compute the cache utilization per group
    print(r"\ constrain the cache footprint of the individual stencils")
    for index, _ in enumerate(sequence):
        print(str(capacity // SIZE_OF_VALUE) + " n%xyz" + str(index) + " - " +
              str(sizes[0] * sizes[1] * sizes[2]) + " f%" + str(index) + " >= 0")

def compute_planes(sequence, dependencies, digits, halos, sizes):
    """
    compute the number of boundary planes
    """
    # multiply the number of boundary operations with the number of tiles
    def multiply_boundaries(variable, dimension, index, digits, halo, limit):
        """
        multiply the tile counts
        """
        limit = 2 * halo * limit
        for digit in digits:
            res = variable + "%n" + dimension + str(index) + "_" + str(digit)
            val = variable + "%" + dimension + str(index)
            mul = "n%" + dimension + str(index) + "_" + str(digit)
            print(res + " - " + str(limit) + " " + mul + " <= 0")
            print(res + " - " + val + " <= 0")
            print(res + " - " + val + " - " + str(limit) + " " + mul + " >= " + str(-limit))
    def sum_boundaries(variable, dimension, index, digits):
        """
        sum the number of tiles
        """
        prefix = variable + "%n" + dimension + str(index)
        terms = " - ".join([str(2**x) + " " + prefix + "_" + str(x) for x in digits])
        print(prefix + " - " + terms + " = 0")
    # compute the number of boundary cache and memory accesses
    print(r"\ multiply the boundary cost by the number of planes")
    for index, stencil in enumerate(sequence):
        limit = len(dependencies[stencil])
        multiply_boundaries("r", "x", index, digits[0], halos[0], limit)
        multiply_boundaries("r", "y", index, digits[1], halos[1], limit)
        multiply_boundaries("r", "z", index, digits[2], halos[2], limit)
        sum_boundaries("r", "x", index, digits[0])
        sum_boundaries("r", "y", index, digits[1])
        sum_boundaries("r", "z", index, digits[2])
    for index, stencil in enumerate(sequence):
        limit = 1
        multiply_boundaries("e", "x", index, digits[0], halos[0], limit)
        multiply_boundaries("e", "y", index, digits[1], halos[1], limit)
        multiply_boundaries("e", "z", index, digits[2], halos[2], limit)
        sum_boundaries("e", "x", index, digits[0])
        sum_boundaries("e", "y", index, digits[1])
        sum_boundaries("e", "z", index, digits[2])
    # compute the total number of read and write boundary lines
    def constrain_base(index, dimension, halo, size):
        """
        set the read write boundary width
        """
        print("rw%n" + dimension +  str(index) + " - " +
              "e%n" + dimension + str(index) + " - " +
              str(2 * halo * size) + " rw%" + str(index) + " >= " + str(-2 * halo * size))
    for index, stencil in enumerate(sequence):
        constrain_base(index, "x", halos[0], sizes[0])
        constrain_base(index, "y", halos[1], sizes[1])
        constrain_base(index, "z", halos[2], sizes[2])
    # compute the total number of write boundary lines
    def constrain_write(index, dimension, halo, size):
        """
        set the read write boundary width
        """
        print("w%n" + dimension +  str(index) + " - " +
              "e%n" + dimension + str(index) + " - " +
              str(2 * halo * size) + " w%" + str(index) + " >= " + str(-2 * halo * size))
    for index, stencil in enumerate(sequence):
        constrain_write(index, "x", halos[0], sizes[0])
        constrain_write(index, "y", halos[1], sizes[1])
        constrain_write(index, "z", halos[2], sizes[2])
    # set the stream boundary widths to the maximum of the read and read and write widths
    def constrain_streams(index, dimension):
        """
        set streams to the maximum of the read and the read or write boundary
        """
        print("s%n" + dimension +  str(index) + " - " +
              "w%n" + dimension + str(index) + " - " +
              "r%n" + dimension + str(index) + " >= 0")
    for index, stencil in enumerate(sequence):
        constrain_streams(index, "x")
        constrain_streams(index, "y")
        constrain_streams(index, "z")

def compute_costs(sequence, dependencies, fetches, sizes, digits, halos, memory, cache, overlap):
    """
    compute the number of body and peel points
    """
    # define helper methods
    def multiply_peels(index, digits, limit):
        """
        multiply the peel cost with the number of tiles
        """
        for digit in digits:
            res = "p%n" + str(index) + "_" + str(digit)
            val = "p%" + str(index)
            mul = "n%x" + str(index) + "_" + str(digit)
            print(res + " - " + str(limit) + " " + mul + " <= 0")
            print(res + " - " + val + " <= 0")
            print(res + " - " + val + " - " + str(limit) + " " + mul + " >= " + str(-limit))
    def sum_peels(index, digits):
        """
        sum the peel for all tiles
        """
        prefix = "p%n" + str(index)
        terms = " - ".join([str(2**x) + " " + prefix + "_" + str(x) for x in digits])
        print(prefix + " - " + terms + " = 0")
    # evaluate the cost model
    print(r"\ evaluate the cost model")
    for index, stencil in enumerate(sequence):
        # compute the memory body time
        base = memory["RW BODY"]
        stream = memory["ST BODY"]
        # compute the body cost
        print("b%m" + str(index) + " - " +
              " - ".join([
                  str(base * sizes[0] * sizes[1] * sizes[2]) + " rw%" + str(index),
                  str(base * sizes[1] * sizes[2]) + " rw%nx" + str(index),
                  str(base * sizes[0] * sizes[2]) + " rw%ny" + str(index),
                  str(base * sizes[0] * sizes[1]) + " rw%nz" + str(index)]) + " - " +
              " - ".join([
                  str(stream * sizes[0] * sizes[1] * sizes[2]) + " s%" + str(index),
                  str(stream * sizes[1] * sizes[2]) + " s%nx" + str(index),
                  str(stream * sizes[0] * sizes[2]) + " s%ny" + str(index),
                  str(stream * sizes[0] * sizes[1]) + " s%nz" + str(index)]) + " >= 0")
        # compute the cache body time
        const = fetches[stencil] * cache["BODY"]
        print("b%c" + str(index) + " - " +
              " - ".join([str(const * sizes[1] * sizes[2]) + " e%nx" + str(index),
                          str(const * sizes[0] * sizes[2]) + " e%ny" + str(index),
                          str(const * sizes[0] * sizes[1]) + " e%nz" + str(index)]) + " >= " +
              str(const * sizes[0] * sizes[1] * sizes[2]))
        # compute the max of memory and cache boundary cost
        print("b%" + str(index) + " - b%m" + str(index) + " >= 0")
        print("b%" + str(index) + " - b%c" + str(index) + " >= 0")
        # compute the memory peel time and count it only if there are memory accesses
        base = memory["RW PEEL"]
        stream = memory["ST PEEL"]
        print("p%" + str(index) + " - " +
              " - ".join([str(base * sizes[1] * sizes[2]) + " rw%" + str(index),
                          str(base * sizes[1]) + " rw%nz" + str(index),
                          str(base * sizes[2]) + " rw%ny" + str(index)]) + " - " +
              " - ".join([str(stream * sizes[1] * sizes[2]) + " s%" + str(index),
                          str(stream * sizes[1]) + " s%nz" + str(index),
                          str(stream * sizes[2]) + " s%ny" + str(index)]) + " >= 0")
        # compute the memory peel limit
        limit = (base * sizes[1] * sizes[2] +
                 base * sizes[1] * (2 * halos[2] * sizes[2]) +
                 base * sizes[2] * (2 * halos[1] * sizes[1]) +
                 stream * sizes[1] * sizes[2] * len(dependencies[stencil]) +
                 stream * sizes[1] * len(dependencies[stencil]) * (2 * halos[2] * sizes[2]) +
                 stream * sizes[2] * len(dependencies[stencil]) * (2 * halos[1] * sizes[1]))
        # compute the cache peel time
        const = fetches[stencil] * cache["PEEL"]
        print("p%" + str(index) + " - " +
              " - ".join([str(const * sizes[1]) + " e%nz" + str(index),
                          str(const * sizes[2]) + " e%ny" + str(index)]) +
              " >= " + str(const * sizes[1] * sizes[2]))
        # compute an upper bound for the peel execution time
        limit = max(limit,
                    (const * sizes[1] * sizes[2] +
                     const * sizes[1] * (2 * halos[2] * sizes[2])  +
                     const * sizes[2] * (2 * halos[1] * sizes[1])))
        # multiply the peel execution time with the number of tiles along the x dimension
        multiply_peels(index, digits[0], limit)
        sum_peels(index, digits[0])
        # compute the total time
        print("t%" + str(index) + " - " +
              str(overlap) + " b%" + str(index) + " - " +
              str(1.0-overlap) + " b%m" + str(index) + " - " +
              str(1.0-overlap) + " b%c" + str(index) + " - " +
              "p%n" + str(index) + " = 0")

def delimit_search(sequence, constraints):
    """
    add external constraints that limit the search space
    """
    # add the group constraints
    if "GROUPS" in constraints:
        for stencil, group in constraints["GROUPS"]:
            index = sequence.index(stencil)
            print("g%" + str(index) + " = " + str(group))
    # add tile count constraints
    if "TILING" in constraints:
        for dimension, stencil, value in constraints["TILING"]:
            if value > 0:
                print("n%" + dimension + str(sequence.index(stencil)) + " >= " + str(value + 1))
            else:
                print("n%" + dimension + str(sequence.index(stencil)) + " <= " + str(-value - 1))

def define_constraints(program):
    """
    define the constraints
    """
    print("Subject To")
    # get relevant collections
    sequence = program["SEQUENCE"]
    outputs = program["OUTPUTS"]
    utilization = program["UTILIZATION"]
    dependencies = program["DEPENDENCIES"]
    fetches = program["FETCHES"]
    halos = [program["HX"], program["HY"], program["HZ"]]
    cores = program["MACHINE"]["CORES"]
    sizes = [program["X"], program["Y"], program["Z"]]
    digits = [program["DX"], program["DY"], program["DZ"]]
    capacity = program["MACHINE"]["CAPACITY"]
    memory = program["MEMORY"]
    cache = program["CACHE"]
    overlap = program["OVERLAP"]
    slack = program["SLACK"]
    constraints = program["CONSTRAINTS"]
    # compute the group indexes and tile sizes
    compute_groups(sequence)
    compute_memory(sequence, outputs, dependencies)
    compute_tiles(sequence, cores, sizes, digits, slack)
    # compute the evaluation and access
    compute_boundaries(sequence, dependencies, halos)
    # constrain the cache utilization
    compute_footprint(sequence, utilization)
    constrain_footprint(sequence, sizes, capacity)
    # compute the memory and cache costs
    compute_planes(sequence, dependencies, digits, halos, sizes)
    compute_costs(sequence, dependencies, fetches, sizes, digits, halos, memory, cache, overlap)
    # add external constraints that limit the search space
    delimit_search(sequence, constraints)

def define_general(program):
    """
    define general variables
    """
    print("General")
    # get relevant collections
    sequence = program["SEQUENCE"]
    dependencies = program["DEPENDENCIES"]
    # define the group index variables
    print(" ".join(["g%" + str(index) for index, _ in enumerate(sequence)]))
    # define the evaluation domains
    print(" ".join(["e%xm" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%xp" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%ym" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%yp" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%zm" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%zp" + str(index) for index, _ in enumerate(sequence)]))
    # define the access ranges
    for stencil, accesses in dependencies.items():
        index = sequence.index(stencil)
        print(" ".join(["a%xm" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["a%xp" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["a%ym" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["a%yp" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["a%zm" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["a%zp" + str(index) + "_" + name for name, _ in accesses.items()]))
    # define the number of tiles per dimension
    print(" ".join(["n%x" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["n%y" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["n%z" + str(index) for index, _ in enumerate(sequence)]))
    # define the tile count products
    print(" ".join(["n%xy" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["n%xyz" + str(index) for index, _ in enumerate(sequence)]))
    # define the loop count multipliers
    print(" ".join(["x%" + str(index) for index, _ in enumerate(sequence)]))
    # define the tile size multipliers
    print(" ".join(["y%x" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["y%y" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["y%z" + str(index) for index, _ in enumerate(sequence)]))
    # define the domain sizes per dimension
    print(" ".join(["d%x" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["d%y" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["d%z" + str(index) for index, _ in enumerate(sequence)]))
    # define the helper variables to compute the domain size variable
    for index, _ in enumerate(sequence):
        print(" ".join(["d%x" + str(index) + "_" + str(digit) for digit in program["DX"]]))
        print(" ".join(["d%y" + str(index) + "_" + str(digit) for digit in program["DY"]]))
        print(" ".join(["d%z" + str(index) + "_" + str(digit) for digit in program["DZ"]]))
    # define the helper variables to compute the number of tiles
    for index, _ in enumerate(sequence):
        print(" ".join(["n%xy" + str(index) + "_" + str(digit) for digit in program["DY"]]))
    for index, _ in enumerate(sequence):
        print(" ".join(["n%xyz" + str(index) + "_" + str(digit) for digit in program["DZ"]]))
    # define the cache footprint
    print(" ".join(["f%" + str(index) for index, _ in enumerate(sequence)]))
    # define the evaluation boundary (cache fetches and memory costs)
    print(" ".join(["e%x" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%y" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%z" + str(index) for index, _ in enumerate(sequence)]))
    # define the helper variables to multiply the evaluation boundary by the number of tiles
    for index, _ in enumerate(sequence):
        print(" ".join(["e%nx" + str(index) + "_" + str(digit) for digit in program["DX"]]))
        print(" ".join(["e%ny" + str(index) + "_" + str(digit) for digit in program["DY"]]))
        print(" ".join(["e%nz" + str(index) + "_" + str(digit) for digit in program["DZ"]]))
    # define the total number of evaluation boundary lines (cache fetches and memory costs)
    print(" ".join(["e%nx" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%ny" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["e%nz" + str(index) for index, _ in enumerate(sequence)]))
    # define the number of read, write, and read or write streams
    print(" ".join(["r%" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["w%" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["s%" + str(index) for index, _ in enumerate(sequence)]))
    # define the number of boundary reads per stencil
    for stencil, accesses in dependencies.items():
        index = sequence.index(stencil)
        print(" ".join(["r%xm" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["r%xp" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["r%ym" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["r%yp" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["r%zm" + str(index) + "_" + name for name, _ in accesses.items()]))
        print(" ".join(["r%zp" + str(index) + "_" + name for name, _ in accesses.items()]))
    # define the number of boundary reads
    print(" ".join(["r%x" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["r%y" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["r%z" + str(index) for index, _ in enumerate(sequence)]))
    # define the helper variables to compute the total number of boundary reads
    for index, _ in enumerate(sequence):
        print(" ".join(["r%nx" + str(index) + "_" + str(digit) for digit in program["DX"]]))
        print(" ".join(["r%ny" + str(index) + "_" + str(digit) for digit in program["DY"]]))
        print(" ".join(["r%nz" + str(index) + "_" + str(digit) for digit in program["DZ"]]))
    # define the total number of boundary reads
    print(" ".join(["r%nx" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["r%ny" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["r%nz" + str(index) for index, _ in enumerate(sequence)]))
    # define the total number of boundary writes
    print(" ".join(["w%nx" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["w%ny" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["w%nz" + str(index) for index, _ in enumerate(sequence)]))
    # define the total number of boundary streams
    print(" ".join(["s%nx" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["s%ny" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["s%nz" + str(index) for index, _ in enumerate(sequence)]))
    # define the total number of boundary reads or writes
    print(" ".join(["rw%nx" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["rw%ny" + str(index) for index, _ in enumerate(sequence)]))
    print(" ".join(["rw%nz" + str(index) for index, _ in enumerate(sequence)]))

def define_binary(program):
    """
    define binary variables
    """
    print("Binary")
    # get relevant collections
    sequence = program["SEQUENCE"]
    dependencies = program["DEPENDENCIES"]
    # force group flags to one if the group indexes of the stencils do not match
    for high in range(1, len(sequence)):
        print(" ".join(["g%" + str(low) + "#" + str(high) for low in range(high)]))
    # number of tiles per dimension
    for index, _ in enumerate(sequence):
        print(" ".join(["n%x" + str(index) + "_" + str(digit) for digit in program["DX"]]))
        print(" ".join(["n%y" + str(index) + "_" + str(digit) for digit in program["DY"]]))
        print(" ".join(["n%z" + str(index) + "_" + str(digit) for digit in program["DZ"]]))
    # define the per stencil read variables
    for index, stencil in enumerate(sequence):
        accesses = dependencies[stencil].keys()
        print(" ".join(["r%" + str(index) + "_" + name for name in accesses]))
    # define the read or write variables
    print(" ".join(["rw%" + str(index) for index, _ in enumerate(sequence)]))

def generate_lp(name, program):
    """
    generate the linear program
    """
    # redirect the output
    tmp = open(name + ".lp", 'w')
    out = sys.stdout
    sys.stdout = tmp
    # print program
    define_target(program)
    define_constraints(program)
    # print variables
    define_general(program)
    define_binary(program)
    print("End")
    sys.stdout = out
    tmp.close()

def solve_lp(name):
    """
    run the solver
    """
    program = name + ".lp"
    cleaned = name + "R.lp"
    result = name + ".sol"
    if exists(result):
        remove(result)
    # replace - - with +
    with open(program) as infile, open(cleaned, 'w') as outfile:
        for line in infile:
            line = line.replace("- -", "+ ")
            outfile.write(line)
    remove(program)
    copyfile(cleaned, program)
    remove(cleaned)
    # start cplex and set the mipgap parameter before running the optimization
    proc = Popen(["cplex"], stdin=PIPE)
    proc.communicate(b"read " + program.encode() + b"\n" +
                     b"mipopt\n" +
                     b"write " + result.encode() + b"\n" +
                     b"quit\n")
    # proc.communicate(b"set mip tolerances mipgap 0.0001\n" +
    #                  b"read " + program.encode() + b"\n" +
    #                  b"mipopt\n" +
    #                  b"write " + result.encode() + b"\n" +
    #                  b"quit\n")
    print("done!")

def parse_lp(name, program):
    """
    parse the solver output
    """
    # prepare parsing
    sequence = program["SEQUENCE"]
    fetches = program["FETCHES"]
    memory = program["MEMORY"]
    cache = program["CACHE"]
    cores = program["MACHINE"]["CORES"]
    overlap = program["OVERLAP"]
    sizes = [program["X"], program["Y"], program["Z"]]
    result = name + ".sol"
    # search xml for important information
    if exists(result):
        print("parsing " + result)
        dom = parse(result)
        variables = list(map(
            lambda var: (var.attributes["name"].value, round(float(var.attributes["value"].value))),
            dom.getElementsByTagName("variable")
        ))
        # extract the group indexes
        print("group indexes:")
        indexes = []
        last = 0
        for index, stencil in enumerate(sequence):
            name = "g%" + str(index)
            val = next((y for (x, y) in variables if x == name))
            print(stencil + "\t-> value " + str(val))
            last = max(last, val)
            indexes.append(val)
        # compute the group information
        groups = [{"STENCILS" : []} for x in range(max(indexes) + 1)]
        for index, stencil in zip(indexes, sequence):
            groups[index]["STENCILS"].append(stencil)
        # extract the tiling information
        tile_sizes = []
        tile_counts = []
        for index, _ in enumerate(sequence):
            print("tiles stencil " + str(index) + ":")
            count = 1
            tile_size = []
            tile_count = []
            for offset, dimension in enumerate(["x", "y", "z"]):
                # extract the size information
                buffer = dimension
                name = "n%" + dimension + str(index)
                val = next((y for (x, y) in variables if x == name))
                # compute the actual tile sizes and to overhead
                size = (sizes[offset] + val - 1) // val
                tile_size.append(size)
                tile_count.append(val)
                count *= val
                buffer += "\t-> value " + str(val)
                buffer += "\t-> size " + str(size)
                buffer += "\t-> total " + str(size * val)
                print(buffer)
            tile_sizes.append(tile_size)
            tile_counts.append(tile_count)
            # print multiple of cores
            name = "x%" + str(index)
            val = next((y for (x, y) in variables if x == name))
            print("slack \t-> loops " + str(val) + "\t-> idle " + str(val * cores - count))
            # print the total tile count
            print(" ==> count " + str(count))
        # store the tiling information
        for index, _ in enumerate(sequence):
            tile_count = tile_counts[index]
            group = groups[indexes[index]]
            for offset, dimension in enumerate(["X", "Y", "Z"]):
                key = "N" + dimension
                if key in group:
                    assert group[key] == tile_count[offset]
                else:
                    group[key] = tile_count[offset]
        # store the tiling information
        program["TILING"] = {"NX" : 1, "NY" : 1, "NZ" : 1,
                             "GROUPS" : [{"GROUPS": [x]} for x in groups]}
        # extract the cache utilization information
        print("stencil cache utilization:")
        for index, stencil in enumerate(sequence):
            count = next((y for (x, y) in variables if x == "f%" + str(index)))
            buffer = stencil + "\t-> count " + str(count)
            # compute the utilization
            tile = tile_sizes[index]
            size = count * tile[0] * tile[1] * tile[2] * SIZE_OF_VALUE // 1024
            buffer += "\t-> footprint " + str(size) + " kB"
            print(buffer)
        # print the estimated execution time
        objective = dom.getElementsByTagName("header")[0].attributes["objectiveValue"].value
        print(" ==> estimated execution time [ms] " + objective)
        program["OBJECTIVE"] = objective
        memory_body = []
        memory_peel = []
        cache_body = []
        cache_peel = []
        # compute the cache execution time
        print("cache model:")
        for index, stencil in enumerate(sequence):
            buffer = stencil
            # store the memory access information
            peel0 = next((y for (x, y) in variables if x == "e%x" + str(index)))
            peel1 = next((y for (x, y) in variables if x == "e%y" + str(index)))
            peel2 = next((y for (x, y) in variables if x == "e%z" + str(index)))
            buffer += "\t-> interior " + str(fetches[stencil])
            buffer += "\t-> boundary (" + str(peel0) + ", " + str(peel1) + ", " + str(peel2) + ")"
            # compute the execution times
            body = sizes[0] * sizes[1] * sizes[2]
            body += peel0 * sizes[1] * sizes[2] * tile_counts[index][0]
            body += peel1 * sizes[0] * sizes[2] * tile_counts[index][1]
            body += peel2 * sizes[0] * sizes[1] * tile_counts[index][2]
            body *= fetches[stencil] * cache["BODY"]
            peel = sizes[1] * sizes[2]
            peel += peel1 * sizes[2] * tile_counts[index][1]
            peel += peel2 * sizes[1] * tile_counts[index][2]
            peel *= tile_counts[index][0]
            peel *= fetches[stencil] * cache["PEEL"]
            cache_peel.append(peel)
            cache_body.append(body)
            buffer += "\t-> peel " + "{0:.4f}".format(peel)
            buffer += "\t-> body " + "{0:.4f}".format(body)
            print(buffer)
        # compute the memory execution time
        print("memory model:")
        for index, stencil in enumerate(sequence):
            buffer = stencil
            # store the memory access information
            reads = next((y for (x, y) in variables if x == "r%" + str(index)))
            writes = next((y for (x, y) in variables if x == "w%" + str(index)))
            base = next((y for (x, y) in variables if x == "rw%" + str(index)))
            streams = next((y for (x, y) in variables if x == "s%" + str(index)))
            reads0 = next((y for (x, y) in variables if x == "r%nx" + str(index)))
            reads1 = next((y for (x, y) in variables if x == "r%ny" + str(index)))
            reads2 = next((y for (x, y) in variables if x == "r%nz" + str(index)))
            base0 = next((y for (x, y) in variables if x == "rw%nx" + str(index)))
            base1 = next((y for (x, y) in variables if x == "rw%ny" + str(index)))
            base2 = next((y for (x, y) in variables if x == "rw%nz" + str(index)))
            streams0 = next((y for (x, y) in variables if x == "s%nx" + str(index)))
            streams1 = next((y for (x, y) in variables if x == "s%ny" + str(index)))
            streams2 = next((y for (x, y) in variables if x == "s%nz" + str(index)))
            buffer += "\t-> reads " + str(reads)
            buffer += " (" + str(reads0//tile_counts[index][0]) + ", "
            buffer += str(reads1//tile_counts[index][1]) + ", "
            buffer += str(reads2//tile_counts[index][2]) + ")"
            buffer += "\t-> writes " + str(writes)
            buffer += "\t-> streams " + str(streams)
            buffer += " (" + str(streams0//tile_counts[index][0]) + ", "
            buffer += str(streams1//tile_counts[index][1]) + ", "
            buffer += str(streams2//tile_counts[index][2]) + ")"
            buffer += "\t-> read/write " + str(base)
            buffer += " (" + str(base0//tile_counts[index][0]) + ", "
            buffer += str(base1//tile_counts[index][1]) + ", "
            buffer += str(base2//tile_counts[index][2]) + ")"
            # compute the execution time¨
            body = memory["RW BODY"] * (
                sizes[0] * sizes[1] * sizes[2] * base +
                sizes[1] * sizes[2] * base0 +
                sizes[0] * sizes[2] * base1 +
                sizes[0] * sizes[1] * base2)
            body += memory["ST BODY"] * (
                sizes[0] * sizes[1] * sizes[2] * streams +
                sizes[1] * sizes[2] * streams0 +
                sizes[0] * sizes[2] * streams1 +
                sizes[0] * sizes[1] * streams2)
            peel = memory["RW PEEL"] * (
                sizes[1] * sizes[2] * base +
                sizes[1] * base2 +
                sizes[2] * base1)
            peel += memory["ST PEEL"] * (
                sizes[1] * sizes[2] * streams +
                sizes[1] * streams2 +
                sizes[2] * streams1)
            memory_peel.append(peel)
            memory_body.append(body)
            buffer += "\t-> peel " + "{0:.4f}".format(peel)
            buffer += "\t-> body " + "{0:.4f}".format(body)
            print(buffer)
        # compute objective function
        print("compute max peel plus max body times:")
        peel = sum(list(map(max, memory_peel, cache_peel)))
        body = overlap * sum(list(map(max, memory_body, cache_body)))
        body += (1.0 - overlap) * sum(list(map(lambda x, y: x + y, memory_body, cache_body)))
        overhead = 6 * (program["MEMORY"]["RW BODY"] + program["MEMORY"]["ST BODY"])
        extra = sum([x[0] * x[1] * x[2] * overhead for x in tile_counts])
        total = peel + body + extra
        print(" ==> peel time: " + str(peel))
        print(" ==> body time: " + str(body))
        print(" ==> extra time: " + str(extra))
        print(" ==> total time: " + str(total))

# find optimal stencil program implementation variant
def optimize_program(name, program):
    """
    find optimal implementation variant
    """
    # analyze the stencil access pattern
    compute_dependencies(program)
    compute_sequence(program)
    compute_utilization(program)
    compute_domain(program)
    # generate and solve the linear program
    generate_lp(name, program)
    solve_lp(name)
    # analyze the program output
    parse_lp(name, program)
