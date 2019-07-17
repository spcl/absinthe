# Copyright (c) 2019, ETH Zurich

""" this module generates distributed memory stencil codes """

from os import getcwd
from csv import writer
from collections import deque
from jinja2 import Environment, FileSystemLoader
from subprocess import call
from stencil_analyzer import verify_program, compute_dataflow, compute_boundaries

# compute the program schedule
def compute_schedule(program):
    """
    compute the program schedule
    """
    # compute schedule
    schedule = []
    fifo = deque([None])
    # schedule the program
    for group in program["TILING"]["GROUPS"]:
        # insert synchronization
        wait = fifo.popleft()
        if wait:
            schedule.append(wait)
        # insert computation
        if group["LOOPS"]:
            schedule.append({"TYPE": "COMP", "GROUP": group})
        # insert communication
        if group["HALOS"]:
            put = {"TYPE": "PUT", "GROUP": group}
            schedule.append(put)
            wait = put.copy()
            wait["TYPE"] = "WAIT"
            fifo.append(wait)
        else:
            fifo.append(None)
    program["SCHEDULE"] = schedule

# generate the stencil code
def generate_code(template, name, program):
    """
    generate the code
    """
    # verify the consistency of the configuration
    verify_program(program)
    # compute inputs, outputs and temporaries for all tiling levels
    compute_dataflow(program)
    # compute the boundary information
    compute_boundaries(program)
    # compute the schedule
    compute_schedule(program)
    # render the template
    env = Environment(loader=FileSystemLoader(getcwd()))
    tpl = env.get_template(template)
    code = tpl.render(program)
    # write the code
    with open(name, "w") as file:
        file.write(code)

# generate the makefile
def generate_makefile(name, experiments):
    """
    generate the makefile
    """
    # power flags
    #ccflags = ["-O3", "-std=c++11", "-ffast-math",
    #           "-mcpu=power8", "-fopenmp", "-DNDEBUG"]
    # knl flags
    #ccflags = ["-O3", "-std=c++11", "-ffast-math",
    #           "-mavx512f", "-mavx512cd", "-mavx512er", "-mavx512pf", "-DNDEBUG"]
    ccflags = ["-std=c++11", "-O3", "-ffast-math", "-fopenmp",
               "-DNDEBUG"]
    ldflags = []
    # generate the run script
    with open(name, "w", newline="\n") as file:
        file.write("\n")
        file.write("CC=g++\n")
        file.write("CCFLAGS= \\\n\t" + " \\\n\t".join(ccflags) + "\n")
        file.write("LDFLAGS= \\\n\t" + " \\\n\t".join(ldflags) + "\n\n")
        file.write("all: " + " ".join(experiments.keys()))
        file.write("\n\n")
        for name, _ in experiments.items():
            file.write(name + ": " + name + ".o\n")
            file.write("\t$(CC) $(CCFLAGS) $< -o $@ $(LDFLAGS) \n\n") 
            file.write(name + ".o: " + name + ".cpp\n")
            file.write("\t$(CC) $(CCFLAGS) -c -o $@ $<\n\n")
        file.write("clean:\n")
        file.write("\trm *.o " + " ".join(experiments.keys()))

# build the program
def build_experiment(name):
    """ build program """
    call(["make"])

# generate the run script
def generate_script(name, experiments, cores, runs):
    """ generate the run script """
    # generate the run script
    with open(name, "w", newline="\n") as file:
        file.write("#!/bin/bash -l\n")
        file.write("export OMP_PLACES=cores\n\n")
        file.write("export OMP_PROC_BIND=close\n\n")
        # set the number of threads
        file.write("export OMP_NUM_THREADS=" + str(cores) + "\n\n")
        file.write("export OMP_STACKSIZE=128M\n\n")
        for run in range(runs):
            for name, _ in experiments.items():
                file.write("./" + name + "\n")

# parse the results
def parse_results(results, skip = 16):
    """ convert the print outs of a run to a csv file """
    # analyze the results
    domain = []
    variant = None
    total = []
    halo = []
    pack = []
    wait = []
    put = []
    rows = []
    counter = 0
    with open(results, "r") as file:
        lines = file.readlines()
    for line in lines:
        if line.startswith("   - domain "):
            domain = [int(x) for x in line[len("   - domain "):].split(", ")]
            # activate this if you want to skip the first measurements
            counter = skip
        elif line.startswith("   - variant "):
            variant = str(line[len("   - variant "):]).rstrip()
        elif line.startswith("   - total time (min/median/max) [ms]: "):
            start = len("   - total time (min/median/max) [ms]: ")
            total = [float(x) for x in line[start:].split("/")]
        elif line.startswith("   - halo time (min/median/max) [ms]: "):
            start = len("   - halo time (min/median/max) [ms]: ")
            halo = [float(x) for x in line[start:].split("/")]
        # elif line.startswith("   - pack time (min/median/max) [ms]: "):
        #     start = len("   - pack time (min/median/max) [ms]: ")
        #     pack = [float(x) for x in line[start:].split("/")]
        # elif line.startswith("   - wait time (min/median/max) [ms]: "):
        #     start = len("   - wait time (min/median/max) [ms]: ")
        #     wait = [float(x) for x in line[start:].split("/")]
        # elif line.startswith("   - put time (min/median/max) [ms]: "):
        #     start = len("   - put time (min/median/max) [ms]: ")
        #     put = [float(x) for x in line[start:].split("/")]
            if counter == 0:
                row = [variant]
                row = row + [str(x) for x in domain]
                row = row + [str(x) for x in total]
                row = row + [str(x) for x in halo]
                row = row + [str(x) for x in pack]
                row = row + [str(x) for x in wait]
                row = row + [str(x) for x in put]
                rows.append(row)
            counter = max(0, counter - 1)
    return rows

# write rows to csv file
def write_results(rows, table):
    """ write rows to output table """
    header = [
        "VAR",
        "X", "Y", "Z",
        "TOTAL", "HALO"]
        # "TMIN", "TMED", "TOTAL",
        # "HMIN", "HMED", "HALO",
        # "CMIN", "CMED", "COPY",
        # "WMIN", "WMED", "WAIT",
        # "PMIN", "PMED", "PUT"]
    rows = [header] + rows
    print("-> writing results to " + table)
    with open(table, "w") as file:
        csv = writer(file, delimiter=",", quotechar="'", lineterminator="\n")
        for row in rows:
            csv.writerow(row)
