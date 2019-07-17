# Copyright (c) 2019, ETH Zurich

library(ggplot2)
library(ggrepel)
library(reshape)
library(plyr)
library(L1pack)

# diffusion
setwd(paste(getwd(),"/fastwaves",sep=""))
source("../SPCL_Stats.R")

# prepare the data
estimates <- read.csv(file="estimates.csv", sep=",", stringsAsFactors=FALSE, header=TRUE)
results <- read.csv(file="results.csv", sep=",", stringsAsFactors=FALSE, header=TRUE)

# compute the measured execution time
results$MEA <- results$TOTAL - results$HALO
results <- results[c("VAR", "MEA")]
results <- summarySE(results, measurevar="MEA", groupvars=c("VAR"), conf.interval=.95)
results$COL <- ifelse(results$VAR=="OPT", "A", "C")
results$COL <- ifelse(results$VAR=="HAND", "B", results$COL)
results$COL <- ifelse(results$VAR=="AUTO", "B", results$COL)
results$COL <- ifelse(results$VAR=="MIN", "B", results$COL)
results$COL <- ifelse(results$VAR=="MAX", "B", results$COL)

# merge the tables
data <- merge(estimates, results)

opt <- data[data[,"VAR"] == "OPT",]
auto <- data[data[,"VAR"] == "AUTO",]
maxf <- data[data[,"VAR"] == "MAX",]

delta = ((auto$median/opt$median)-1.0)*100.0
autotuning = sprintf("auto-tuning\n(%.1f%%)", delta)

delta = ((maxf$median/opt$median)-1.0)*100.0
maxfusion = sprintf("max\n(%.1f%%)", delta)

ggsave(file="scatter.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(data, aes(x=EST, y=median, colour=COL, shape=COL)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=0.04, show.legend=FALSE) +
        geom_point(show.legend=FALSE, size=2.4) +        
        geom_abline(intercept=0, slope=1) +
        geom_text_repel(data=subset(data, VAR=="OPT"), aes(label="absinthe"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="HAND"), aes(label="hand"), point.padding=unit(0.08, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="MIN"), aes(label="min"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="MAX"), aes(label="max"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="AUTO"), aes(label=autotuning), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        #xlim(0.56, 1.35) + 
        #ylim(0.56, 1.35) + 
        xlab("estimated time [ms]") + 
        ylab("measured time [ms]") +
        scale_color_manual(values=c("#2b8cbe", "#2b8cbe", "#bae4bc")) +
        scale_shape_manual(values=c(17, 15, 16)) +
        ggtitle("fastwaves (Power)") +
        theme_bw())

# filter data and show the measurements that beat the optimal solution
better <- data[data[,"median"] <= opt$median + 0.01,]
print(better[c("VAR", "EST", "median", "cil", "cih")])

# compute accuracy compared to auto-tuned
print("accuracy")
print(1.0 - (auto$median/opt$median))

print("hand")
hand <- data[data[,"VAR"] == "HAND",]
print(hand[c("VAR", "EST", "median", "cil", "cih")])

print("min")
hand <- data[data[,"VAR"] == "MIN",]
print(hand[c("VAR", "EST", "median", "cil", "cih")])

# slow <- data[data[,"median"] >= 2.9,]
# print(slow[c("VAR", "EST", "median", "cil", "cih")])

# p <- ggplot(data, aes(x=EST, y=median, colour=COL, shape=COL)) +
#         geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=0.025, show.legend=FALSE) +
#         geom_point(show.legend=FALSE) +        
#         geom_abline(intercept=0, slope=1) +
#         geom_text_repel(data=subset(data, VAR=="OPT"), nudge_x=-0.05, nudge_y=-0.0, aes(label="OPT"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="HAND"), nudge_x=-0.1, nudge_y=0.07, aes(label="HAND"), point.padding=unit(0.08, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="MIN"), nudge_x=-0.09, nudge_y=0.15, aes(label="MIN"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="MAX"), nudge_x=0.01, nudge_y=0.15, aes(label="MAX"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="AUTO"), nudge_x=0.2, nudge_y=0.0, aes(label="AUTO"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         xlim(0.46, 1.2) + 
#         ylim(0.46, 1.2) + 
#         xlab("estimated time [ms]") + 
#         ylab("measured time [ms]") +
#         theme_bw() +
#         theme(legend.title=element_blank())

# doc <- pptx()
# doc <- addSlide(doc, "Two Content")
# doc <- addPlot(doc, function() print(p), vector.graphic=TRUE, height=3, width=3)
# writeDoc(doc, file="scatter.pptx") 


# evaluate the auto tuning results
print("auto tuning")
results <- read.csv(file="auto.csv", sep=",", stringsAsFactors=FALSE, header=TRUE)

get_group <- function(name){
   sub('.*-([0-9]+)-.*','\\1', name)
   nums <- regmatches(name, gregexpr('[0-9]+', name))
   return(nums$VAR[1])
}
get_x <- function(name){
   sub('.*-([0-9]+)-.*','\\1', name)
   nums <- regmatches(name, gregexpr('[0-9]+', name))
   return(nums$VAR[2])
}
get_y <- function(name){
   sub('.*-([0-9]+)-.*','\\1', name)
   nums <- regmatches(name, gregexpr('[0-9]+', name))
   return(nums$VAR[3])
}
get_z <- function(name){
   sub('.*-([0-9]+)-.*','\\1', name)
   nums <- regmatches(name, gregexpr('[0-9]+', name))
   return(nums$VAR[4])
}
results$GRP <- apply(results[c("VAR")], 1, function(x) get_group(x[1]))

# compute the measured execution time
results$MEA <- results$TOTAL - results$HALO
results <- results[c("VAR", "GRP", "MEA")]
results <- summarySE(results, measurevar="MEA", groupvars=c("VAR", "GRP"), conf.interval=.95)

total <- 0.0
for(grp in unique(results$GRP)) {
    # extract the data of the given yz plane
    data <- results[results[,"GRP"] == grp,]
    optimum <- min(sapply(data$median, min))
    data <- data[data[,"cil"] <= optimum,]

    print(optimum)
    print(data[c("VAR", "GRP", "median", "cil", "cih")])

    total <- total + optimum
}
print("total time:")
print(total)

# additionally find the optimal tiling with one common tile size!
results$X <- apply(results[c("VAR")], 1, function(x) get_x(x[1]))
results$Y <- apply(results[c("VAR")], 1, function(x) get_y(x[1]))
results$Z <- apply(results[c("VAR")], 1, function(x) get_z(x[1]))

configurations <- unique(results[c("X", "Y", "Z")])
min <- 1000.0
for(i in 1:nrow(configurations))
{
    data <- results[results[,"X"] == configurations[i, 1],]
    data <- data[data[,"Y"] == configurations[i, 2],]
    data <- data[data[,"Z"] == configurations[i, 3],]
    
    time <- sum(data$median)
    if(time < min) {
        min <- time
    }
}

for(i in 1:nrow(configurations))
{
    data <- results[results[,"X"] == configurations[i, 1],]
    data <- data[data[,"Y"] == configurations[i, 2],]
    data <- data[data[,"Z"] == configurations[i, 3],]
    
    time <- sum(data$median)
    if(time == min) {
        print("single tile minimum")
        print(data[c("VAR", "GRP", "median", "cil", "cih")])
        print(min)
    }
}
