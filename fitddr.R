# Copyright (c) 2019, ETH Zurich

library(ggplot2)
library(ggrepel)
library(reshape)
library(plyr)
library(L1pack)

# set the core count
cores <- 4

setwd(paste(getwd(),"/fitddr",sep=""))
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

# precompute the constants
data$bd <- as.numeric(substr(data$VAR, 6, 6)) * 2   
data$inp <- as.numeric(substr(data$VAR, 3, 3))  

data$rwbody <- steps * data$XYZ
data$stbody <- steps * (data$inp + 1) * data$XYZ + steps * data$inp * data$bd * (data$XY + data$XZ + data$YZ)

data$rwpeel <- steps * data$YZ
data$stpeel <- steps * (data$inp + 1) * data$YZ + steps * data$inp * data$bd * (data$Y + data$Z)

# do not train with zero inputs
data <- data[data[,"inp"] >= 1,]

test <- data
training <- data

# try to fit the model
print("training")
model <- lad(TOTAL ~ rwbody + stbody + rwpeel + stpeel - 1, data=training) 

#print("parameters")
#print(coef(model))

# scale the cost to account for the fact that we effectively update one tile per core
print(paste("rw body: ", coef(model)[c("rwbody")] / cores))
print(paste("st body: ", coef(model)[c("stbody")] / cores))
print(paste("rw peel: ", coef(model)[c("rwpeel")] / cores))
print(paste("st peel: ", coef(model)[c("stpeel")] / cores))

# function evaluating the fitting
analyze_error <- function(model, base) {
    base <- base[c("rwbody", "rwpeel", "stbody", "stpeel", "VAR", "TOTAL")]
    base <- summarySE(base, measurevar="TOTAL", groupvars=c("rwbody", "rwpeel", "stbody", "stpeel", "VAR"), conf.interval=.95)
    base$prediction <- predict(model, base)
   
    print("error total :")
    print(paste("r2            : ", 1 - sum((base$median-base$prediction)^2) / sum((base$median-mean(base$median))^2) ))

    print("error for IN1BD0:")
    filtered = base[base[,"VAR"] == "IN1BD0",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for IN2BD0:")
    filtered = base[base[,"VAR"] == "IN2BD0",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for IN3BD0:")
    filtered = base[base[,"VAR"] == "IN3BD0",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
   
    print("error for IN1BD1:")
    filtered = base[base[,"VAR"] == "IN1BD1",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for IN2BD1:")
    filtered = base[base[,"VAR"] == "IN2BD1",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for IN3BD1:")
    filtered = base[base[,"VAR"] == "IN3BD1",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))

    print("error for IN1BD2:")
    filtered = base[base[,"VAR"] == "IN1BD2",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for IN2BD2:")
    filtered = base[base[,"VAR"] == "IN2BD2",]
    print(paste("r2            : ", 1 - sum((filtered$median-filtered$prediction)^2) / sum((filtered$median-mean(filtered$median))^2) ))
    print("error for IN3BD2:")
    filtered = base[base[,"VAR"] == "IN3BD2",]
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
scatter <- scatter[scatter[,"bd"] == 2,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)
trend <- data.frame(X=c(8, 65, 82, 8, 75, 82, 8, 45, 82), VAR=c("IN1BD1", "IN1BD1", "IN1BD1", "IN2BD1", "IN2BD1", "IN2BD1", "IN3BD1", "IN3BD1",  "IN3BD1"))

trend$bd <- as.numeric(substr(trend$VAR, 6, 6)) * 2   
trend$inp <- as.numeric(substr(trend$VAR, 3, 3))  
trend$rwbody <- steps * trend$X * y * z
trend$stbody <- steps * (trend$inp + 1) * trend$X * y * z + steps * trend$inp * trend$bd * (trend$X * y + trend$X * z + y * z)
trend$rwpeel <- steps * y * z
trend$stpeel <- steps * (trend$inp + 1) * y * z + steps * trend$inp * trend$bd * (y + z)
trend$pred <- predict(model, trend)  

ggsave(file="5x5.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=2.5, show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="IN1BD1"), aes(x=X, y=pred, label="i=1,b=1"), nudge_y=-0.03, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==75 & VAR=="IN2BD1"), aes(x=X, y=pred, label="i=2,b=1"), nudge_y=0.04, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==45 & VAR=="IN3BD1"), aes(x=X, y=pred, label="i=3,b=1"), nudge_y=0.03, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(8, 82) + 
        xlab("x (y=5,z=5)") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.01, 0.176)) +
        theme_bw() +
        theme(legend.title=element_blank(), legend.justification=c(0,1), legend.position=c(0.01,0.98)))

ggsave(file="5x5.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=4.0, show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE, size=2.4) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="IN1BD1"), aes(x=X, y=pred, label="i=1,b=1"), nudge_y=-0.02, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==75 & VAR=="IN2BD1"), aes(x=X, y=pred, label="i=2,b=1"), nudge_y=0.03, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==45 & VAR=="IN3BD1"), aes(x=X, y=pred, label="i=3,b=1"), nudge_y=0.02, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(8, 82) + 
        xlab("x") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.0, 0.11)) +
        scale_color_manual(values=c("#bae4bc", "#7bccc4", "#2b8cbe")) +
        ggtitle("slow memory") +
        theme_bw() +
        theme(legend.justification=c(0,1), legend.position=c(0.01,0.98)))

y <- 34
z <- 1
scatter <- test[test[,"Y"] == y,]
scatter <- scatter[scatter[,"Z"] == z,]
scatter <- scatter[scatter[,"bd"] == 2,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)
trend <- data.frame(X=c(8, 65, 82, 8, 75, 82, 8, 45, 82), VAR=c("IN1BD1", "IN1BD1", "IN1BD1", "IN2BD1", "IN2BD1", "IN2BD1", "IN3BD1", "IN3BD1",  "IN3BD1"))

trend$bd <- as.numeric(substr(trend$VAR, 6, 6)) * 2   
trend$inp <- as.numeric(substr(trend$VAR, 3, 3))  
trend$rwbody <- steps * trend$X * y * z
trend$stbody <- steps * (trend$inp + 1) * trend$X * y * z + steps * trend$inp * trend$bd * (trend$X * y + trend$X * z + y * z)
trend$rwpeel <- steps * y * z
trend$stpeel <- steps * (trend$inp + 1) * y * z + steps * trend$inp * trend$bd * (y + z)
trend$pred <- predict(model, trend)  

ggsave(file="34x1.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=2.5, show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="IN1BD1"), aes(x=X, y=pred, label="i=1,b=1"), nudge_y=-0.04, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==75 & VAR=="IN2BD1"), aes(x=X, y=pred, label="i=2,b=1"), nudge_y=0.04, nudge_x=-10, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==45 & VAR=="IN3BD1"), aes(x=X, y=pred, label="i=3,b=1"), nudge_y=0.04, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(8, 82) + 
        xlab("x (y=34,z=1)") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.01, 0.176)) +
        theme_bw() +
        theme(legend.title=element_blank(), legend.justification=c(0,1), legend.position=c(0.01,0.98)))

y <- 1
z <- 13
scatter <- test[test[,"Y"] == y,]
scatter <- scatter[scatter[,"Z"] == z,]
scatter <- scatter[scatter[,"bd"] == 2,]
scatter <- scatter[c("X", "Y", "Z", "VAR", "TOTAL")]
scatter <- summarySE(scatter, measurevar="TOTAL", groupvars=c("X", "Y", "Z", "VAR"), conf.interval=.95)
trend <- data.frame(X=c(8, 65, 82, 8, 75, 82, 8, 45, 82), VAR=c("IN1BD1", "IN1BD1", "IN1BD1", "IN2BD1", "IN2BD1", "IN2BD1", "IN3BD1", "IN3BD1",  "IN3BD1"))

trend$bd <- as.numeric(substr(trend$VAR, 6, 6)) * 2   
trend$inp <- as.numeric(substr(trend$VAR, 3, 3))  
trend$rwbody <- steps * trend$X * y * z
trend$stbody <- steps * (trend$inp + 1) * trend$X * y * z + steps * trend$inp * trend$bd * (trend$X * y + trend$X * z + y * z)
trend$rwpeel <- steps * y * z
trend$stpeel <- steps * (trend$inp + 1) * y * z + steps * trend$inp * trend$bd * (y + z)
trend$pred <- predict(model, trend)  

ggsave(file="1x13.pdf", height=3, width=3, units="in", scale=1.0,
    ggplot(scatter, aes(x=X, y=median, colour=VAR, shape=VAR)) +
        geom_errorbar(aes(ymin=cil, ymax=cih), color="gray", width=2.5, show.legend=FALSE) +
        scale_shape_manual(values=c(15, 17, 18)) +
        geom_point(show.legend=FALSE) +
        geom_text_repel(data=subset(trend, X==65 & VAR=="IN1BD1"), aes(x=X, y=pred, label="i=1,b=1"), nudge_y=-0.02, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==75 & VAR=="IN2BD1"), aes(x=X, y=pred, label="i=2,b=1"), nudge_y=0.04, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_text_repel(data=subset(trend, X==45 & VAR=="IN3BD1"), aes(x=X, y=pred, label="i=3,b=1"), nudge_y=0.03, nudge_x=-1, show.legend=FALSE, point.padding=unit(0.1, "in"), arrow=arrow(length=unit(0.05, "in"))) +
        geom_line(data=trend, aes(x=X, y=pred), show.legend=FALSE) +
        xlim(8, 82) + 
        xlab("x (y=1,z=13)") + ylab("execution time [ms]") +
        #scale_y_continuous(labels=fmt_dcimals(2), limits=c(0.01, 0.176)) +
        theme_bw() +
        theme(legend.title=element_blank(), legend.justification=c(0,1), legend.position=c(0.01,0.98)))
