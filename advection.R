# Copyright (c) 2019, ETH Zurich

library(ggplot2)
library(ggrepel)
library(reshape)
library(plyr)
library(L1pack)

# diffusion
setwd(paste(getwd(),"/advection",sep=""))
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
delta = ((auto$median/opt$median)-1.0)*100.0
autotuning = sprintf("auto-tuning\n(%.1f%%)", delta)

ggsave(file="scatter.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(data, aes(x=EST, y=median, colour=COL, shape=COL)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=0.06, show.legend=FALSE) +
        geom_point(show.legend=FALSE, size=2.4) +        
        geom_abline(intercept=0, slope=1) +
        geom_text_repel(data=subset(data, VAR=="OPT"), aes(label="absinthe"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="HAND"), aes(label="hand"), point.padding=unit(0.2, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="MIN"), aes(label="min"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="MAX"), aes(label="max"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        geom_text_repel(data=subset(data, VAR=="AUTO"), aes(label=autotuning), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
        #xlim(0.46, 1.6) + 
        #ylim(0.46, 1.6) + 
        xlab("estimated time [ms]") + 
        ylab("measured time [ms]") +
        scale_color_manual(values=c("#2b8cbe", "#2b8cbe", "#bae4bc")) +
        scale_shape_manual(values=c(17, 15, 16)) +
        ggtitle("advection (Power)") +
        theme_bw())

# filter data and show the measurements that beat the optimal solution
better <- data[data[,"median"] <= opt$median + 0.01,]
print(better[c("VAR", "EST", "median", "cil", "cih")])

# compute accuracy compared to auto-tuned
print("accuracy")
print(1.0 - (auto$median/opt$median))

# p <- ggplot(data, aes(x=EST, y=median, colour=COL, shape=COL)) +
#         geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=0.014, show.legend=FALSE) +
#         geom_point(show.legend=FALSE) +        
#         geom_abline(intercept=0, slope=1) +
#         geom_text_repel(data=subset(data, VAR=="OPT"), nudge_x=0.01, nudge_y=0.05, aes(label="OPT"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="HAND"), nudge_x=0.0, nudge_y=0.05, aes(label="HAND"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="MIN"), nudge_x=-0.05, nudge_y=0.05, aes(label="MIN"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="MAX"), nudge_x=0.08, nudge_y=0.0, aes(label="MAX"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         geom_text_repel(data=subset(data, VAR=="AUTO"), nudge_x=0.05, nudge_y=-0.038, aes(label="AUTO"), point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in")), show.legend=FALSE) +
#         xlim(0.4, 0.8) + 
#         ylim(0.4, 0.8) + 
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
results$GRP <- apply(results[c("VAR")], 1, function(x) get_group(x[1]))

# compute the measured execution time
results$MEA <- results$TOTAL - results$HALO
results <- results[c("VAR", "GRP", "MEA")]
results <- summarySE(results, measurevar="MEA", groupvars=c("VAR", "GRP"), conf.interval=.95)

for(grp in unique(results$GRP)) {
    # extract the data of the given yz plane
    data <- results[results[,"GRP"] == grp,]
    optimum <- min(sapply(data$median, min))
    data <- data[data[,"cil"] <= optimum,]

    print(optimum)
    print(data[c("VAR", "GRP", "median", "cil", "cih")])
}