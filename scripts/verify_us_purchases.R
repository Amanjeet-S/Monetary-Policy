#!/usr/bin/env Rscript
# Independent standard-R replay of the declared US household-purchase study.
# Usage: Rscript verify_us_purchases.R REPOSITORY OUTPUT_CSV

args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop("Usage: Rscript verify_us_purchases.R REPOSITORY OUTPUT_CSV")
root <- normalizePath(args[1L],mustWork=TRUE)
panel <- read.csv(file.path(root,"data/processed/us_purchase_monthly.csv"),
                  stringsAsFactors=FALSE,na.strings=c("","NA"),check.names=FALSE)
source <- read.csv(file.path(root,"data/processed/us_policy_events.csv"),
                   stringsAsFactors=FALSE,na.strings=c("","NA"),check.names=FALSE)

month_number <- function(s) 12L*as.integer(substr(s,1L,4L))+as.integer(substr(s,6L,7L))-1L
calendar <- month_number(panel$month)
if (nrow(panel) != 812L || anyDuplicated(calendar) || any(diff(calendar) != 1L)) {
  stop("Unique complete monthly source calendar required")
}
if (nrow(source) != 263L || anyDuplicated(source$date) || !identical(source$date,sort(source$date))) {
  stop("Complete original meeting sample differs")
}
if (any(!is.na(panel$raw_monthly_intention[calendar < month_number("1969-01")]))) {
  stop("Pre-coverage policy placeholders cannot be observed intentions")
}
if (any(!is.na(panel$raw_monthly_intention[calendar > month_number("1996-12")]))) {
  stop("No post-coverage intention fill is permitted")
}
level_names <- c("durable","nondurable","services","real_disposable_income","pce_price")
for (name in level_names) if (any(!is.na(panel[[name]]) & panel[[name]] <= 0)) stop("Positive levels required")

qr_fit <- function(X,Y) {
  X <- as.matrix(X);Y <- as.matrix(Y);n <- nrow(X);k <- ncol(X)
  if (n <= k || any(!is.finite(X)) || any(!is.finite(Y))) stop("Invalid regression domain")
  decomposition <- qr(X,tol=1e-10,LAPACK=FALSE)
  if (decomposition$rank != k) stop("Full design rank required")
  Q <- qr.Q(decomposition);R <- qr.R(decomposition)
  beta <- matrix(0,k,ncol(Y));operator <- matrix(0,n,k)
  beta[decomposition$pivot,] <- backsolve(R,crossprod(Q,Y))
  operator[,decomposition$pivot] <- Q %*% t(backsolve(R,diag(k)))
  list(beta=beta,residual=Y-X %*% beta,operator=operator,leverage=rowSums(Q*Q),rank=k)
}

forecasts <- c("intercept","OLDTARG","GRADM","GRAD0","GRAD1","GRAD2",
               "IGRDM","IGRD0","IGRD1","IGRD2","GRAYM","GRAY0","GRAY1","GRAY2",
               "IGRYM","IGRY0","IGRY1","IGRY2","GRAU0")
purge <- qr_fit(as.matrix(source[,forecasts]),source$raw_intention)
reconstructed_innovation <- as.numeric(purge$residual)
source_error <- max(abs(reconstructed_innovation-source$supplied_innovation))
processed_error <- max(abs(reconstructed_innovation-source$innovation))
if (max(source_error,processed_error) > 1e-10) stop("Independent source purge does not agree")
source$independent_innovation <- reconstructed_innovation

at <- function(name,date) panel[[name]][match(date,calendar)]
categories <- c("durable","nondurable","services")
histories <- c(categories,"real_disposable_income")

design <- function(policy_lags=12L,exclude_reserves=FALSE,start=1L) {
  event <- source[source$date >= "1971-01-12" & source$date <= "1996-12-17",,drop=FALSE]
  if (nrow(event) != 238L) stop("Declared common event mask differs")
  if (exclude_reserves) event <- event[!(event$month >= "1979-10" & event$month <= "1982-10"),,drop=FALSE]
  dates <- month_number(event$month);n <- nrow(event)
  W <- as.matrix(event[,forecasts])
  for (name in histories) W <- cbind(W,100*log(at(name,dates-1L)/at(name,dates-2L)))
  for (name in histories) W <- cbind(W,100*log(at(name,dates-1L)/at(name,dates-13L)))
  W <- cbind(W,100*log(at("pce_price",dates-1L)/at("pce_price",dates-13L)),at("funds_rate",dates-1L))
  for (lag in seq_len(policy_lags)) {
    if (any(dates-lag < month_number("1969-01"))) stop("Unobserved policy prehistory")
    W <- cbind(W,at("raw_monthly_intention",dates-lag))
  }
  Y <- matrix(numeric(0),n,0)
  offsets <- seq.int(start,start+35L)
  for (name in categories) {
    future_dates <- outer(dates,offsets,"+")
    future <- matrix(at(name,as.vector(future_dates)),nrow=n,ncol=36L)
    base <- at(name,dates-1L)
    Y <- cbind(Y,100*(future/base-1))
  }
  past_dates <- outer(dates,seq_len(12L),"-")
  past <- matrix(at("durable",as.vector(past_dates)),nrow=n,ncol=12L)
  predetermined <- rowSums(past/at("durable",dates-13L))-12
  Y <- cbind(Y,event$financial_change,predetermined)
  z <- event$independent_innovation/.25;raw <- event$raw_intention/.25
  if (ncol(W) != 29L+policy_lags || ncol(Y) != 110L ||
      any(!is.finite(c(W,Y,z,raw)))) stop("Required declared input is unavailable")
  list(dates=dates,W=W,z=z,raw=raw,Y=Y,event_dates=event$date)
}

# Direct event-pair kernel includes cross-products between same-month events.
# Algebraically equal to summing scores within a month before applying HAC.
calendar_covariance <- function(score,dates,L,k) {
  n <- nrow(score)
  K <- pmax(1-abs(outer(dates,dates,"-"))/(L+1),0)
  V <- crossprod(score,K %*% score)*n/(n-k)
  V <- (V+t(V))/2
  if (any(diag(V) <= 0)) stop("Nondegenerate retained marginal covariance required")
  V
}
interval <- function(value,variance,alpha=.05) {
  se <- sqrt(max(variance,0));q <- qnorm(1-alpha/2)
  list(estimate=as.numeric(value),se=se,lower=as.numeric(value-q*se),
       upper=as.numeric(value+q*se),p_two_sided=if (se == 0) NULL else 2*pnorm(-abs(value)/se))
}

quadratic_set <- function(A,B,C) {
  if (any(!is.finite(c(A,B,C)))) stop("Finite quadratic coefficients required")
  if (A == 0) {
    if (B == 0) {
      if (C <= 0) {kind <- "whole_real_line";parts <- list(list(lower=NULL,upper=NULL))}
      else {kind <- "empty";parts <- list()}
    } else if (B > 0) {kind <- "left_halfline";parts <- list(list(lower=NULL,upper=-C/B))}
    else {kind <- "right_halfline";parts <- list(list(lower=-C/B,upper=NULL))}
  } else {
    discriminant <- B*B-4*A*C
    if (discriminant < 0) {
      if (A < 0) {kind <- "whole_real_line";parts <- list(list(lower=NULL,upper=NULL))}
      else {kind <- "empty";parts <- list()}
    } else if (discriminant == 0) {
      if (A < 0) {kind <- "whole_real_line";parts <- list(list(lower=NULL,upper=NULL))}
      else {v <- -B/(2*A);kind <- "isolated_point";parts <- list(list(lower=v,upper=v))}
    } else {
      signed_root <- if (B >= 0) sqrt(discriminant) else -sqrt(discriminant)
      q <- -(B+signed_root)/2;roots <- sort(c(q/A,C/q))
      if (A > 0) {kind <- "bounded_interval";parts <- list(list(lower=roots[1L],upper=roots[2L]))}
      else {kind <- "two_rays";parts <- list(list(lower=NULL,upper=roots[1L]),list(lower=roots[2L],upper=NULL))}
    }
  }
  contains <- if (!length(parts)) FALSE else any(vapply(parts,function(p) {
    (is.null(p$lower) || p$lower <= 0) && (is.null(p$upper) || p$upper >= 0)
  },logical(1)))
  list(kind=kind,intervals=parts,contains_zero=contains,quadratic_coefficients=c(A,B,C))
}

fit_case <- function(policy_lags=12L,L=41L,leverage_adjusted=FALSE,exclude_reserves=FALSE,start=1L) {
  D <- design(policy_lags,exclude_reserves,start);X <- cbind(D$z,D$W)
  F <- qr_fit(X,D$Y);n <- nrow(X);k <- ncol(X)
  coefficient <- as.numeric(F$beta[1L,]);score <- F$residual*F$operator[,1L]
  if (leverage_adjusted) score <- score/(1-F$leverage)
  V <- calendar_covariance(score,D$dates,L,k)
  A <- matrix(0,9L,ncol(D$Y));labels <- character(9L)
  bounds <- list(c(1L,12L),c(13L,36L),c(1L,36L));window_names <- c("first12","later24","full36")
  for (j in seq_along(categories)) for (w in seq_along(bounds)) {
    row <- (j-1L)*3L+w;index <- (j-1L)*36L+seq.int(bounds[[w]][1L],bounds[[w]][2L])
    A[row,index] <- .01;labels[row] <- paste(categories[j],window_names[w],sep="_")
  }
  cb <- as.numeric(A %*% coefficient);cv <- A %*% V %*% t(A);cs <- score %*% t(A)
  windows <- list()
  for (j in seq_along(labels)) windows[[labels[j]]] <- list(pointwise95=interval(cb[j],cv[j,j]),
                                                          endpoint_family95=interval(cb[j],cv[j,j],.05/9))
  financial <- coefficient[109L];financial_variance <- V[109L,109L]
  cross <- as.numeric(A[3L,] %*% V[,109L]);reduced <- cb[3L];vr <- cv[3L,3L]
  first <- financial/.25;vf <- financial_variance/.25^2;cross_scaled <- cross/.25
  critical <- qnorm(.975)^2
  AR <- quadratic_set(first^2-critical*vf,-2*reduced*first+2*critical*cross_scaled,reduced^2-critical*vr)
  if (AR$contains_zero != (windows$durable_full36$pointwise95$p_two_sided >= .05)) stop("AR zero-test mismatch")
  point <- if (financial == 0) NULL else reduced*.25/financial
  profiles <- lapply(seq_len(36L),function(h) {
    row <- list(months=h)
    for (j in seq_along(categories)) {
      vector <- numeric(ncol(D$Y));vector[(j-1L)*36L+seq_len(h)] <- .01
      index <- (j-1L)*36L+h
      response <- as.numeric(crossprod(vector,coefficient));variance <- as.numeric(crossprod(vector,V %*% vector))
      row[[categories[j]]] <- list(cumulative_pointwise95=interval(response,variance),
                                   cumulative_profile_family95=interval(response,variance,.05/36),
                                   flow_pointwise95=interval(coefficient[index],V[index,index]))
    }
    row
  })
  raw_fit <- qr_fit(cbind(D$raw,D$W),D$Y)
  fwl <- list(coefficient_max_abs_error=max(abs(F$beta[1L,]-raw_fit$beta[1L,])),
              residual_max_abs_error=max(abs(F$residual-raw_fit$residual)),
              coefficient_loading_max_abs_error=max(abs(F$operator[,1L]-raw_fit$operator[,1L])),
              leverage_max_abs_error=max(abs(F$leverage-raw_fit$leverage)))
  if (max(unlist(fwl)) > 1e-8) stop("Current-purge FWL invariance fails")
  identities <- list(coefficient_max_abs_error=max(vapply(seq_len(3L),function(j) {
                      abs(cb[3L*j]-cb[3L*j-2L]-cb[3L*j-1L])
                    },numeric(1))),
                    score_max_abs_error=max(vapply(seq_len(3L),function(j) {
                      max(abs(cs[,3L*j]-cs[,3L*j-2L]-cs[,3L*j-1L]))
                    },numeric(1))))
  comparisons <- list()
  for (j in c(6L,9L)) {
    vector <- numeric(9L);vector[3L] <- 1;vector[j] <- -1
    label <- if (j == 6L) "durable_minus_nondurable" else "durable_minus_services"
    comparisons[[label]] <- interval(sum(vector*cb),as.numeric(crossprod(vector,cv %*% vector)),.05/2)
  }
  scaled <- sweep(X,2L,sqrt(colSums(X*X)),"/");singular <- svd(scaled,nu=0L,nv=0L)$d
  list(n=n,distinct_event_months=length(unique(D$dates)),calendar_span_months=max(D$dates)-min(D$dates)+1L,
       first_event=D$event_dates[1L],last_event=tail(D$event_dates,1L),columns=k,residual_df=n-k,
       policy_lags=policy_lags,bandwidth=L,leverage_adjusted=leverage_adjusted,outcome_start_offset=start,
       maximum_leverage=max(F$leverage),scaled_design_condition_number=max(singular)/min(singular),
       windows=windows,window_order=labels,window_covariance=cv,category_comparisons_family95=comparisons,
       profiles=profiles,financial=list(rate_response_pp=interval(financial,financial_variance),
         hac_t_squared=financial^2/financial_variance,durable36_covariance=cross,
         rate_normalised_ratio_per25bp=point,rate_normalised_AR95=AR),
       predetermined_durable12=interval(coefficient[110L],V[110L,110L]),
       purge_FWL_invariance=fwl,window_identities=identities)
}

primary <- fit_case()
sensitivity <- list(six_policy_lags=fit_case(policy_lags=6L),
                     twenty_four_policy_lags=fit_case(policy_lags=24L),
                     short_bandwidth=fit_case(L=35L),long_bandwidth=fit_case(L=47L),
                     leverage_adjusted_HAC=fit_case(leverage_adjusted=TRUE),
                     exclude_reserves_targeting=fit_case(exclude_reserves=TRUE),
                     event_month_start=fit_case(start=0L))
D <- design();X <- cbind(D$z,D$W);cumulative <- rowSums(D$Y[,1:36L])/100
deletions <- lapply(seq_len(nrow(X)),function(i) {
  F <- qr_fit(X[-i,,drop=FALSE],cumulative[-i])
  list(deleted_event=D$event_dates[i],durable36_estimate=as.numeric(F$beta[1L,1L]))
})

# The two explicitly recorded crossed diagnostics do not replace the primary.
crossed_full <- list(outside_episode_leverage_adjusted=fit_case(exclude_reserves=TRUE,leverage_adjusted=TRUE),
                     outside_episode_twenty_four_policy_lags=fit_case(exclude_reserves=TRUE,policy_lags=24L))
crossed_checks <- lapply(crossed_full,function(fit) {
  response <- fit$windows$durable_full36$pointwise95
  list(n=fit$n,columns=fit$columns,policy_lags=fit$policy_lags,bandwidth=fit$bandwidth,
       maximum_leverage=fit$maximum_leverage,pointwise95=response,
       diagnostic_family95=interval(response$estimate,response$se^2,.05/3),financial=fit$financial)
})
full_fit <- qr_fit(X,cumulative)
kept <- !(substr(D$event_dates,1L,7L) >= "1979-10" & substr(D$event_dates,1L,7L) <= "1982-10")
subset_fit <- qr_fit(X[kept,,drop=FALSE],cumulative[kept])
n <- nrow(X);ns <- sum(kept);k <- ncol(X)
joint <- matrix(0,n,2L)
joint[,1L] <- full_fit$operator[,1L]*full_fit$residual[,1L]*sqrt(n/(n-k))
joint[kept,2L] <- subset_fit$operator[,1L]*subset_fit$residual[,1L]*sqrt(ns/(ns-k))
K <- pmax(1-abs(outer(D$dates,D$dates,"-"))/42,0)
joint_covariance <- crossprod(joint,K %*% joint)
joint_covariance <- (joint_covariance+t(joint_covariance))/2
expected_marginals <- c(primary$windows$durable_full36$pointwise95$se^2,
                       sensitivity$exclude_reserves_targeting$windows$durable_full36$pointwise95$se^2)
if (max(abs(diag(joint_covariance)-expected_marginals)) > 1e-10) stop("Embedded joint marginals differ")
difference <- as.numeric(subset_fit$beta[1L,1L]-full_fit$beta[1L,1L])
contrast <- c(-1,1);contrast_variance <- as.numeric(crossprod(contrast,joint_covariance %*% contrast))
sample_contrast <- list(subset_minus_primary=difference,joint_covariance_order=c("full","outside_episode"),
                        joint_covariance=joint_covariance,pointwise95=interval(difference,contrast_variance),
                        diagnostic_family95=interval(difference,contrast_variance,.05/3),
                        source_event_count=n,subset_event_count=ns)

records <- list()
emit <- function(path,value,type) {
  if (type == "number") value <- format(value,digits=17,scientific=TRUE,trim=TRUE)
  else if (type == "logical") value <- if (value) "true" else "false"
  else if (type == "null") value <- ""
  records[[length(records)+1L]] <<- data.frame(quantity=path,value=as.character(value),type=type,stringsAsFactors=FALSE)
}
flatten <- function(value,path) {
  if (is.null(value)) emit(path,NULL,"null")
  else if (is.matrix(value)) {
    for (i in seq_len(nrow(value))) for (j in seq_len(ncol(value))) emit(paste(path,i-1L,j-1L,sep="."),value[i,j],"number")
  } else if (is.list(value)) {
    labels <- names(value)
    for (i in seq_along(value)) flatten(value[[i]],paste(path,if (is.null(labels)) i-1L else labels[i],sep="."))
  } else if (length(value)>1L) {
    for (i in seq_along(value)) flatten(value[i],paste(path,i-1L,sep="."))
  } else if (is.numeric(value)) emit(path,value,"number")
  else if (is.logical(value)) emit(path,value,"logical")
  else if (is.character(value)) emit(path,value,"string")
  else stop("Unsupported output value")
}
flatten(primary,"primary");flatten(sensitivity,"sensitivity");flatten(deletions,"single_event_deletions")
flatten(crossed_checks,"diagnostics.crossed_checks");flatten(sample_contrast,"diagnostics.sample_contrast")
output <- do.call(rbind,records)
if (anyDuplicated(output$quantity)) stop("Repeated output key")
dir.create(dirname(args[2L]),recursive=TRUE,showWarnings=FALSE)
write.csv(output,args[2L],row.names=FALSE,na="")
source_checks <- data.frame(quantity=c("source_purge_rank","source_purge_replay_max_abs_error",
                                       "processed_innovation_max_abs_error","complete_source_events",
                                       "primary_events","prehistory_guard","next_full_months_start","next_full_months_end"),
                            value=c(purge$rank,source_error,processed_error,nrow(source),primary$n,1,1,36))
write.csv(source_checks,paste0(args[2L],".source_checks.csv"),row.names=FALSE)
cat("Independent US household-purchase quantities:",nrow(output),"\n")
