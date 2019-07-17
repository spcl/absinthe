# Absinthe

Absinthe is an optimization framework to tune stencil programs. It learns a performance model and selects optimal code transformations according to the model. 

The paper "Absinthe: Learning an Analytical Performance Model to Fuse and Tile Stencil Codes in One Shot" (Tobias Gysi, Tobias Grosser, and Torsten Hoefler) provides further implementation details. The software was developed by SPCL (ETH Zurich).

This README gives an overview on how to learn the performance model and optimize the stencil programs.

## Training

The scripts fitcache.py and fitddr.py generate the training stencils to learn the performance model parameters. Before running the scripts we adapt the core count to the target system.

```
# set the core count of the target system
CORES = 4
```

To train Absinthe, we next generate the training files.

```
python ./fitcache.py -g -f ./fitcache
python ./fitddr.py -g -f ./fitddr
```

We then change to the fitcache and fitddr folders to build and run the training files.

```
cd ./fitcache
make 
./run.sh > output.txt
cd ..
python ./fitcache.py -p output.txt -f ./fitcache
```

```
cd ./fitddr
make 
./run.sh > output.txt
cd ..
python ./fitddr.py -p output.txt -f ./fitddr
```

To learn the performance model parameters, we run the fitcache.R and fitddr.R scripts. We first set the core count

```
# set the core count
cores <- 4
```

and then run the scripts.

```
Rscript ./fitcache.R
Rscript ./fitddr.R
```

As a result, we get the performance model parameters.

```
fast memory / cache
[1] "body:  9.44349025644442e-08"
[1] "peel:  9.95340542431222e-07"
```

```
slow memory / ddr
[1] "training"
[1] "rw body:  -2.23277083932771e-07"
[1] "st body:  5.70758516005299e-07"
[1] "rw peel:  -1.24949326618662e-06"
[1] "st peel:  5.253636118141e-06"
```

## Optimization

We next set the machine parameters in the files fastwaves.py, advection.py, and diffusion.py which implement the example stencil sequences.

```
"MACHINE" : {"CORES" : 4, "CAPACITY" : 85*1024},
"MEMORY" : {"RW BODY" : -2.23e-7, "ST BODY": 5.71e-7, "RW PEEL" : -1.25e-6, "ST PEEL" : 5.25e-6},
"CACHE" : {"BODY" : 9.44e-8, "PEEL" : 9.95e-7},
```

Once the parameters are set we can run the optimization to generate different optimization variants.

```
python .\fastwaves.py -e -g -f .\fastwaves
python .\advection.py -e -g -f .\advection
python .\diffusion.py -e -g -f .\diffusion
```

Note that the hand-tuned and the auto-tuned variants are hard coded in the scripts.

To generate the plots for the different implementation variants, we extract the results and run the R scripts.

```
python ./fastwaves.py -p output.txt -f ./fastwaves
python ./advection.py -p output.txt -f ./advection
python ./diffusion.py -p output.txt -f ./diffusion

Rscript ./fastwaves.r
Rscript ./advection.r
Rscript ./diffusion.r
```



