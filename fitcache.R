# Copyright (c) 2019, ETH Zurich

library(ggplot2)
library(ggrepel)
library(reshape)
library(plyr)
library(L1pack)

# set the core count
cores <- 4

setwd(paste(getwd(),"/fitcache",sep=""))
source("../SPCL_Stats.R")

# prepare the data 
data <- read.csv(file="results.csv", sep=",", stringsAsFactors=FALSE, header=TRUE)

# compute model variables
data$XYZ <- (data$X * data$Y * data$Z) / (2 * 2 * 5 * cores)
data$XY <- (data$X * data$Y) / 4
data$XZ <- (data$X * data$Z) / (2 * 5 * cores)
data$YZ <- (data$Y * data$Z) / (2 * 5 * cores)
data$X <- data$X / 2
data$Y <- data$Y / 2
data$Z <- data$Z / (5 * cores)

steps <- 9

# train model on all data
data$fac <- as.numeric(substring(data$VAR, 3))
data$body <- data$fac * steps * data$XYZ
data$peel <- data$fac * steps * data$YZ

data <- data[data[,"fac"] >= 10,]

test <- data
training <- data

# try to fit the model
print("training")
model <- lad(TOTAL ~ body + peel - 1, data=training)
#print(summary(model))
#print("parameters")
#print(coef(model))

# scale the cost to account for the fact that we effectively update one tile per core
body <- coef(model)[c("body")] / cores
peel <- coef(model)[c("peel")] / cores

print(paste("body: ", body))
print(paste("peel: ", peel))

# function evaluating the fitting
analyze_error <- function(model, base) {
    base <- base[c("body", "peel", "VAR", "TOTAL")]
    base <- summarySE(base, measurevar="TOTAL", groupvars=c("body", "peel", "VAR"), conf.interval=.95)
    base$prediction <- predict(model, base)
   
    print("error total :")
    print(paste("r2            : ", 1 - sum((base$median-base$prediction)^2) / sum((base$median-mean(base$median))^2) ))

    print("error for PT12:")
    filtered = base[base[,"VAR"] == "PT12",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for PT16:")
    filtered = base[base[,"VAR"] == "PT16",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for PT20:")
    filtered = base[base[,"VAR"] == "PT20",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
}

# analyze the fitting for the different stencil variants
analyze_error(model, test)

fmt_dcimals <- function(decimals=0){
   # return a function responpsible for formatting the 
   # axis labels with a given number of decimals 
   function(x) as.character(format(round(x, decimals), nsmall = decimals))
}

# plot selected tile sizes
y <- 5
z <- 5
scatter <- test[test[,"Y"] == y,]
scatter <- scatter[scatter[,"Z"] == z,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)

trend <- data.frame(X=c(8, 65, 82, 8, 70, 82, 8, 40, 82), VAR=c("PT12", "PT12", "PT12", "PT16", "PT16", "PT16", "PT20", "PT20", "PT20"))

trend$fac <- as.numeric(substring(trend$VAR, 3))
trend$body <- trend$fac * steps * trend$X * y * z
trend$peel <- trend$fac * steps * y * z
trend$pred <- predict(model, trend)

ggsave(file="5x5.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=4, show.legend=FALSE) +        
        geom_point(show.legend=FALSE, size=2.4) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="PT12"), aes(x=X, y=pred, label="p=12"), nudge_y=-0.015, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==70 & VAR=="PT16"), aes(x=X, y=pred, label="p=16"), nudge_y=-0.005, nudge_x=-0.01, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==40 & VAR=="PT20"), aes(x=X, y=pred, label="p=20"), nudge_y=0.015, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(6, 84) + 
        xlab("x") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.0, 0.073)) +
        scale_color_manual(values=c("#bae4bc", "#7bccc4", "#2b8cbe")) +
        ggtitle("fast memory") +
        theme_bw() +
        theme(legend.justification=c(0,1), legend.position=c(0.01,0.98)))

yz <- 24
scatter <- test[test[,"YZ"] == 24,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)

trend <- data.frame(X=c(8, 65, 82, 8, 70, 82, 8, 40, 82), VAR=c("PT12", "PT12", "PT12", "PT16", "PT16", "PT16", "PT20", "PT20", "PT20"))

trend$fac <- as.numeric(substring(trend$VAR, 3))
trend$body <- trend$fac * steps * trend$X * yz
trend$peel <- trend$fac * steps * yz
trend$pred <- predict(model, trend)

ggsave(file="24.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=2.5, show.legend=FALSE) +        
        geom_point(show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="PT12"), aes(x=X, y=pred, label="p=12"), nudge_y=-0.02, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==70 & VAR=="PT16"), aes(x=X, y=pred, label="p=16"), nudge_y=0.03, nudge_x=-0.01, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==40 & VAR=="PT20"), aes(x=X, y=pred, label="p=20"), nudge_y=0.02, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(6, 84) + 
        xlab("x  (yz=24)") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.001, 0.115)) +
        theme_bw() +
        theme(legend.title=element_blank(), legend.justification=c(0,1), legend.position=c(0.01,0.98)))

yz <- 13
scatter <- test[test[,"YZ"] == 13,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)

trend <- data.frame(X=c(8, 65, 82, 8, 70, 82, 8, 40, 82), VAR=c("PT12", "PT12", "PT12", "PT16", "PT16", "PT16", "PT20", "PT20", "PT20"))

trend$fac <- as.numeric(substring(trend$VAR, 3))
trend$body <- trend$fac * steps * trend$X * yz
trend$peel <- trend$fac * steps * yz
trend$pred <- predict(model, trend)

ggsave(file="13.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=2.5, show.legend=FALSE) +        
        geom_point(show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="PT12"), aes(x=X, y=pred, label="p=12"), nudge_y=-0.014, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==70 & VAR=="PT16"), aes(x=X, y=pred, label="p=16"), nudge_y=0.025, nudge_x=-0.01, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==40 & VAR=="PT20"), aes(x=X, y=pred, label="p=20"), nudge_y=0.025, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(6, 84) + 
        xlab("x  (yz=10)") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.001, 0.115)) +
        theme_bw() +
        theme(legend.title=element_blank(), legend.justification=c(0,1), legend.position=c(0.01,0.98)))

yz <- 39
scatter <- test[test[,"YZ"] == 39,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)

trend <- data.frame(X=c(8, 65, 82, 8, 70, 82, 8, 55, 82), VAR=c("PT12", "PT12", "PT12", "PT16", "PT16", "PT16", "PT20", "PT20", "PT20"))

trend$fac <- as.numeric(substring(trend$VAR, 3))
trend$body <- trend$fac * steps * trend$X * yz
trend$peel <- trend$fac * steps * yz
trend$pred <- predict(model, trend)

ggsave(file="39.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=2.5, show.legend=FALSE) +        
        geom_point(show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="PT12"), aes(x=X, y=pred, label="p=12"), nudge_y=-0.02, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==70 & VAR=="PT16"), aes(x=X, y=pred, label="p=16"), nudge_y=-0.01, nudge_x=-0.01, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==55 & VAR=="PT20"), aes(x=X, y=pred, label="p=20"), nudge_y=0.02, nudge_x=-2, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(6, 84) + 
        xlab("x  (yz=39)") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.001, 0.115)) +
        theme_bw() +
        theme(legend.title=element_blank(), legend.justification=c(0,1), legend.position=c(0.01,0.98)))
