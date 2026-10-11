#!/usr/bin/env Rscript
# Causal loading and predetermined-outcome checks using standard R.
# Usage: Rscript verify_causal_sensitivity.R REPOSITORY OUTPUT_CSV

month_number <- function(x) {
  12L*as.integer(substr(x,1L,4L)) + as.integer(substr(x,6L,7L)) - 1L
}

fit_qr <- function(X,Y) {
  X <- as.matrix(X); Y <- as.matrix(Y)
  decomposition <- qr(X,tol=1e-10,LAPACK=FALSE)
  n <- nrow(X); k <- ncol(X)
  if (decomposition$rank != k || n <= k || any(!is.finite(X)) || any(!is.finite(Y))) {
    stop("Invalid or deficient regression")
  }
  Q <- qr.Q(decomposition); R <- qr.R(decomposition)
  b <- matrix(0,k,ncol(Y)); loading <- matrix(0,n,k)
  b[decomposition$pivot,] <- backsolve(R,crossprod(Q,Y))
  loading[,decomposition$pivot] <- Q %*% t(backsolve(R,diag(k)))
  list(b=b,e=Y-X %*% b,loading=loading)
}

hac <- function(score,calendar,L=18L,k=74L) {
  n <- nrow(score)
  V <- crossprod(score)
  for (i in seq_len(n-1L)) {
    distance <- calendar-calendar[i]
    later <- which(distance > 0L & distance <= L)
    if (length(later)) {
      weighted <- colSums(score[later,,drop=FALSE]*(1-distance[later]/(L+1)))
      cross <- tcrossprod(score[i,],weighted)
      V <- V+cross+t(cross)
    }
  }
  V <- V*n/(n-k)
  (V+t(V))/2
}

args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop("Usage: Rscript verify_causal_sensitivity.R REPOSITORY OUTPUT_CSV")
root <- normalizePath(args[1L],mustWork=TRUE)
panel <- read.csv(file.path(root,"data/processed/monthly_panel.csv"),
                  stringsAsFactors=FALSE,na.strings=c("","NA"),check.names=FALSE)
calendar <- month_number(panel$month)
if (any(diff(calendar) != 1L)) stop("Consecutive calendar required")
at <- function(x,t) x[match(t,calendar)]
d <- panel$durable_index; nd <- panel$nondurable_index; p <- panel$hicp_index
gd <- 100*log(d/at(d,calendar-1L)); gn <- 100*log(nd/at(nd,calendar-1L))
inflation <- 100*log(p/at(p,calendar-12L))
m <- panel$shock_MP_median/.1; c <- panel$shock_CBI_median/.1
dates <- seq.int(month_number("2000-01"),month_number("2025-08"))
Z <- cbind(rep(1,length(dates)),
           vapply(2:12,function(j) as.numeric(dates %% 12L+1L == j),numeric(length(dates))))
for (lag in 1:12) {
  Z <- cbind(Z,at(gd,dates-lag),at(gn,dates-lag),at(inflation,dates-lag),
             at(m,dates-lag),at(c,dates-lag))
}
X <- cbind(at(m,dates),at(c,dates),Z)
if (nrow(X) != 308L || ncol(X) != 74L) stop("Unchanged primary design required")
y <- 100*(log(at(d,dates+12L))-log(at(d,dates-1L))
          -log(at(nd,dates+12L))+log(at(nd,dates-1L)))
F <- fit_qr(X,y)
score <- F$loading[,1:2,drop=FALSE]*as.numeric(F$e)
V <- hac(score,dates)
R <- fit_qr(cbind(at(m+c,dates),Z),y)
W <- fit_qr(cbind(at(m+c,dates),Z),at(c,dates))
values <- c(beta_m=F$b[1L,1L],beta_c=F$b[2L,1L],gamma=R$b[1L,1L],weight=W$b[1L,1L],
            theta=F$b[2L,1L]-F$b[1L,1L])
for (i in 1:2) for (j in 1:2) values[paste0("primary_cov_",i,"_",j)] <- V[i,j]
for (a in c(0,.1,.25,.5,1)) {
  direction <- c(1-a,a)
  response <- as.numeric(crossprod(direction,F$b[1:2,1L]))
  se <- sqrt(as.numeric(crossprod(direction,V %*% direction)))
  prefix <- paste0("loading_",a,"_")
  values[paste0(prefix,"response")] <- response
  values[paste0(prefix,"se")] <- se
  values[paste0(prefix,"ellipse_low")] <- response-sqrt(qchisq(.95,2))*se
  values[paste0(prefix,"ellipse_high")] <- response+sqrt(qchisq(.95,2))*se
}
yd <- 100*log(at(d,dates-13L)/at(d,dates-26L))
yn <- 100*log(at(nd,dates-13L)/at(nd,dates-26L))
PF <- fit_qr(X,cbind(yd,yn,yd-yn))
pscore <- do.call(cbind,lapply(1:3,function(j) {
  PF$loading[,1:2,drop=FALSE]*PF$e[,j]
}))
PV <- hac(pscore,dates)
for (outcome in 1:3) {
  b <- PF$b[1:2,outcome]
  index <- (2L*outcome-1L):(2L*outcome)
  covariance <- PV[index,index]
  stat <- as.numeric(crossprod(b,solve(covariance,b)))
  prefix <- paste0("predetermined_",outcome,"_")
  values[paste0(prefix,"beta_m")] <- b[1L]
  values[paste0(prefix,"beta_c")] <- b[2L]
  values[paste0(prefix,"wald")] <- stat
  values[paste0(prefix,"p_value")] <- pchisq(stat,2,lower.tail=FALSE)
  values[paste0(prefix,"bonferroni_p_value")] <- min(1,3*pchisq(stat,2,lower.tail=FALSE))
  for (i in 1:2) for (j in 1:2) values[paste0(prefix,"cov_",i,"_",j)] <- covariance[i,j]
}
dir.create(dirname(args[2L]),recursive=TRUE,showWarnings=FALSE)
write.csv(data.frame(quantity=names(values),value=as.numeric(values)),args[2L],row.names=FALSE)
cat("Causal sensitivity checks written to",args[2L],"\n")
