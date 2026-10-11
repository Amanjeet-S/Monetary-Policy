#!/usr/bin/env Rscript
# Independent joint construction and period checks using standard R.

month_number <- function(x) {
  12L*as.integer(substr(x,1,4))+as.integer(substr(x,6,7))-1L
}

fit_qr <- function(X,y) {
  d <- qr(X,tol=1e-10,LAPACK=FALSE)
  n <- nrow(X); k <- ncol(X)
  if(d$rank!=k || n<=k || any(!is.finite(X)) || any(!is.finite(y))) stop('Invalid regression design')
  Q <- qr.Q(d); R <- qr.R(d)
  b <- numeric(k); b[d$pivot] <- backsolve(R,crossprod(Q,y))
  e <- drop(y-X%*%b)
  loading <- matrix(0,n,k)
  loading[,d$pivot] <- Q%*%t(backsolve(R,diag(k)))
  list(b=b,e=e,loading=loading,n=n,k=k)
}

hac <- function(I,dates,L) {
  # Actual pairwise calendar distances, independently of the Python embedding.
  V <- crossprod(I)
  for(i in seq_len(nrow(I)-1L)) {
    later <- which(dates-dates[i]>0 & dates-dates[i]<=L)
    if(length(later)) {
      other <- colSums(I[later,,drop=FALSE]*(1-(dates[later]-dates[i])/(L+1)))
      term <- tcrossprod(I[i,],other)
      V <- V+term+t(term)
    }
  }
  (V+t(V))/2
}

make_design <- function(panel,last,family='median') {
  calendar <- month_number(panel$month)
  dates <- seq.int(month_number('2000-01'),month_number(last))
  at <- function(x,where) x[match(where,calendar)]
  D <- panel$durable_index; N <- panel$nondurable_index; P <- panel$hicp_index
  gD <- 100*log(D/at(D,calendar-1L)); gN <- 100*log(N/at(N,calendar-1L))
  inflation <- 100*log(P/at(P,calendar-12L))
  m <- panel[[paste0('shock_MP_',family)]]/.10
  c <- panel[[paste0('shock_CBI_',family)]]/.10
  Z <- cbind(1,vapply(2:12,function(j) as.numeric(dates%%12L+1L==j),numeric(length(dates))))
  for(lag in 1:12) Z <- cbind(Z,at(gD,dates-lag),at(gN,dates-lag),
                            at(inflation,dates-lag),at(m,dates-lag),at(c,dates-lag))
  Y <- 100*(log(at(D,dates+12L)/at(N,dates+12L))-
             log(at(D,dates-1L)/at(N,dates-1L)))
  list(dates=dates,Z=Z,m=at(m,dates),c=at(c,dates),Y=Y)
}

coordinate_fit <- function(d) {
  # The independent calculation orders nuisance controls before the current shocks.
  kZ <- ncol(d$Z)
  F <- fit_qr(cbind(d$Z,d$m,d$c),d$Y)
  R <- fit_qr(cbind(d$Z,d$m+d$c),d$Y)
  W <- fit_qr(cbind(d$Z,d$m+d$c),d$c)
  w <- W$b[kZ+1]; theta <- F$b[kZ+2]-F$b[kZ+1]
  gap <- R$b[kZ+1]-F$b[kZ+1]
  scores <- cbind(R$loading[,kZ+1]*W$e,
                  (F$loading[,kZ+2]-F$loading[,kZ+1])*F$e)*sqrt(F$n/(F$n-F$k))
  direct <- (R$loading[,kZ+1]*R$e-F$loading[,kZ+1]*F$e)*sqrt(F$n/(F$n-F$k))
  if(abs(gap-w*theta)>1e-8 || max(abs(direct-drop(scores%*%c(theta,w))))>1e-8) stop('Influence identity failure')
  list(dates=d$dates,a=c(w,theta),gap=gap,I=scores)
}

trust_min <- function(Q,b,constant) {
  es <- eigen((Q+t(Q))/2,symmetric=TRUE)
  # eigen() returns descending eigenvalues; no reliance on Python ordering.
  values <- es$values; g <- drop(crossprod(es$vectors,b))/2
  scale <- max(1,abs(values),sqrt(sum(g^2)))
  tol <- 128*.Machine$double.eps*scale
  lower <- max(0,-min(values)); denominators <- values+lower
  singular <- abs(denominators)<=tol
  compatible <- sqrt(sum(g[singular]^2))<=tol
  coordinates <- numeric(length(g))
  coordinates[!singular] <- -g[!singular]/denominators[!singular]
  if(compatible && sqrt(sum(coordinates^2))<=1+1e-12) {
    lambda <- lower
    if(lower>tol) coordinates[which(singular)[1]] <- sqrt(max(0,1-sum(coordinates^2)))
  } else {
    secular <- function(lambda) sum((g/(values+lambda))^2)-1
    left <- lower
    if(any(singular)) left <- lower+.Machine$double.eps*max(1,lower)
    right <- max(1,lower+scale)
    while(secular(right)>0) right <- lower+2*(right-lower)
    lambda <- uniroot(secular,c(left,right),tol=1e-13)$root
    coordinates <- -g/(values+lambda)
  }
  u <- drop(es$vectors%*%coordinates)
  stationarity <- sqrt(sum(((Q+lambda*diag(length(b)))%*%u+b/2)^2))
  if(stationarity>1e-8*scale || sqrt(sum(u^2))>1+1e-8 ||
     abs(lambda*(sum(u^2)-1))>1e-8*scale || min(values+lambda)<-1e-8*scale) stop('Trust-region certificate failure')
  drop(constant+crossprod(b,u)+crossprod(u,Q%*%u))
}

image <- function(a,V,B) {
  R <- t(chol(V))*sqrt(qchisq(.95,length(a)))
  Q <- t(R)%*%B%*%R; b <- drop(2*t(R)%*%B%*%a); constant <- drop(t(a)%*%B%*%a)
  c(low=trust_min(Q,b,constant),high=-trust_min(-Q,-b,-constant))
}

comparison <- function(left,right,name,L) {
  dates <- sort(unique(c(left$dates,right$dates)))
  I <- matrix(0,length(dates),4)
  I[match(left$dates,dates),1:2] <- left$I
  I[match(right$dates,dates),3:4] <- right$I
  V <- hac(I,dates,L); a <- c(left$a,right$a)
  B <- matrix(0,4,4); B[1,2] <- B[2,1] <- -.5; B[3,4] <- B[4,3] <- .5
  gradient <- drop(2*B%*%a)
  difference <- right$gap-left$gap
  se <- sqrt(drop(t(gradient)%*%V%*%gradient))
  bounds <- image(a,V,B)
  critical <- qnorm(1-.05/8)
  endpoints <- cbind(a-critical*sqrt(diag(V)),a+critical*sqrt(diag(V)))
  left_products <- as.vector(outer(endpoints[1,],endpoints[2,]))
  right_products <- as.vector(outer(endpoints[3,],endpoints[4,]))
  row <- data.frame(comparison=name,bandwidth=L,difference=difference,se=se,
     equality_p=2*pnorm(-abs(difference/se)),ellipse_low=bounds['low'],ellipse_high=bounds['high'],
     ellipse_frontier=max(abs(bounds)),rectangle_low=min(right_products)-max(left_products),
     rectangle_high=max(right_products)-min(left_products),
     regular_frontier=abs(difference)+qnorm(.95)*se,row.names=NULL)
  for(i in 1:4) row[[paste0('a',i)]] <- a[i]
  for(i in 1:4) for(j in 1:4) row[[paste0('V',i,j)]] <- V[i,j]
  row
}

regime <- function(d,L) {
  post <- as.numeric(d$dates>=month_number('2019-01'))
  X <- cbind(d$Z,post,d$m,d$c,post*d$m,post*d$c)
  F <- fit_qr(X,d$Y); n <- F$n; k <- F$k
  I <- F$loading*F$e*sqrt(n/(n-k))
  V <- hac(I,d$dates,L)
  idx <- (k-1):k; difference <- F$b[idx]; v <- V[idx,idx]
  statistic <- drop(t(difference)%*%solve(v,difference))
  data.frame(bandwidth=L,n=n,k=k,policy_interaction=difference[1],
      information_interaction=difference[2],V11=v[1,1],V12=v[1,2],V22=v[2,2],
      chi2=statistic,p=pchisq(statistic,2,lower.tail=FALSE))
}

main <- function() {
  args <- commandArgs(trailingOnly=TRUE)
  if(length(args)!=3) stop('Usage: Rscript verify_joint_stability.R ROOT COMPARISON_CSV REGIME_CSV')
  root <- normalizePath(args[1],mustWork=TRUE)
  panel <- read.csv(file.path(root,'data/processed/monthly_panel.csv'),stringsAsFactors=FALSE,na.strings=c('','NA'))
  full <- make_design(panel,'2025-08'); pm <- make_design(panel,'2025-08','pm'); early <- make_design(panel,'2018-12')
  left <- coordinate_fit(full); right_pm <- coordinate_fit(pm); right_early <- coordinate_fit(early)
  rows <- rbind(comparison(left,right_pm,'construction',18),comparison(left,right_pm,'construction',17),
                comparison(left,right_early,'sample_period',18),comparison(left,right_early,'sample_period',17))
  tests <- rbind(regime(full,18),regime(full,17))
  for(path in args[2:3]) dir.create(dirname(path),recursive=TRUE,showWarnings=FALSE)
  write.csv(rows,args[2],row.names=FALSE); write.csv(tests,args[3],row.names=FALSE)
  cat('Independent joint contrasts and regime checks written.\n')
}

if(sys.nframe()==0L) main()
