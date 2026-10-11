#!/usr/bin/env Rscript
# Independently reconstruct declared future-policy projections in standard R.
# Usage: Rscript verify_future_policy.R REPOSITORY OUTPUT_CSV

args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 2L) stop("Usage: Rscript verify_future_policy.R REPOSITORY OUTPUT_CSV")
root <- normalizePath(args[1L],mustWork=TRUE)
panel <- read.csv(file.path(root,"data/processed/future_policy_panel.csv"),
                  stringsAsFactors=FALSE,na.strings=c("","NA"),check.names=FALSE)

month_number <- function(s) {
  12L*as.integer(substr(s,1L,4L))+as.integer(substr(s,6L,7L))-1L
}
month_name <- function(n) sprintf("%04d-%02d",n %/% 12L,n %% 12L+1L)
calendar <- month_number(panel$month)
if (length(calendar) != 428L || anyDuplicated(calendar) || any(diff(calendar) != 1L)) {
  stop("Primitive panel must contain a unique consecutive monthly calendar")
}
for (name in c("manufacturing","industrial","hicp","durable","nondurable")) {
  value <- panel[[name]]
  if (any(!is.na(value) & (!is.finite(value) | value <= 0))) stop("Invalid observed level")
}

# This QR calculation is independent of the retained Python implementation.
qr_fit <- function(X,Y) {
  X <- as.matrix(X); Y <- as.matrix(Y)
  n <- nrow(X); k <- ncol(X)
  if (n <= k || any(!is.finite(X)) || any(!is.finite(Y))) stop("Invalid fit domain")
  decomposition <- qr(X,tol=1e-10,LAPACK=FALSE)
  if (decomposition$rank != k) stop("Full rank required")
  Q <- qr.Q(decomposition); R <- qr.R(decomposition)
  beta <- matrix(0,k,ncol(Y)); operator <- matrix(0,n,k)
  beta[decomposition$pivot,] <- backsolve(R,crossprod(Q,Y))
  operator[,decomposition$pivot] <- Q %*% t(backsolve(R,diag(k)))
  list(beta=beta,residual=Y-X %*% beta,operator=operator,
       leverage=rowSums(Q*Q),rank=decomposition$rank)
}

# Pairwise calendar distances rather than array lags construct the kernel.
calendar_covariance <- function(score,dates,L,k) {
  n <- nrow(score)
  if (n != length(dates) || any(diff(dates) <= 0) || L < 0) stop("Invalid calendar")
  distance <- abs(outer(dates,dates,"-"))
  kernel <- pmax(1-distance/(L+1),0)
  V <- crossprod(score,kernel %*% score)*n/(n-k)
  V <- (V+t(V))/2
  if (min(eigen(V,symmetric=TRUE,only.values=TRUE)$values) <= 0) {
    stop("Positive-definite empirical score covariance required for retained cases")
  }
  V
}

at <- function(name,date) panel[[name]][match(date,calendar)]
growth <- function(date) 100*log(at("manufacturing",date)/at("manufacturing",date-1L))
inflation <- function(date) 100*log(at("hicp",date)/at("hicp",date-12L))

design <- function(h=12L,p=2L) {
  dates <- seq.int(month_number("2005-01"),month_number("2016-01"))
  W <- cbind(1,at("target",dates)/.10,at("delphic",dates)/.10)
  for (lag in seq_len(p)) {
    prior <- dates-lag
    W <- cbind(W,growth(prior),inflation(prior),
               at("target",prior)/.10,at("delphic",prior)/.10,
               at("odyssean",prior)/.10,at("yield_1y_change_pp",prior)/.10,
               at("yield_3m_change_pp",prior)/.10)
  }
  Z <- at("odyssean",dates)/.10
  financial <- cbind(at("yield_1y_change_pp",dates)/.10,
                     at("yield_3m_change_pp",dates)/.10)
  if (h < 0) {
    future <- dates-1L; past <- dates-13L
  } else {
    future <- dates+h; past <- dates-1L
  }
  change <- function(name) 100*log(at(name,future)/at(name,past))
  responses <- cbind(change("manufacturing"),change("industrial"),
                     change("durable")-change("nondurable"))
  if (length(dates) != 133L || ncol(W) != 3L+7L*p ||
      any(!is.finite(c(W,Z,financial,responses)))) stop("Declared sample differs")
  list(dates=dates,W=W,Z=Z,financial=financial,responses=responses)
}

# Exact zero branches preserve topology; no small coefficient is discarded.
# Stable q-formula independently calculates the nondegenerate endpoints.
quadratic_set <- function(A,B,C) {
  if (any(!is.finite(c(A,B,C)))) stop("Finite quadratic coefficients required")
  if (A == 0) {
    if (B == 0) {
      if (C <= 0) {
        kind <- "whole_real_line"; intervals <- list(list(lower=NULL,upper=NULL))
      } else {
        kind <- "empty"; intervals <- list()
      }
    } else if (B > 0) {
      kind <- "left_halfline"; intervals <- list(list(lower=NULL,upper=-C/B))
    } else {
      kind <- "right_halfline"; intervals <- list(list(lower=-C/B,upper=NULL))
    }
  } else {
    discriminant <- B*B-4*A*C
    if (discriminant < 0) {
      if (A < 0) {
        kind <- "whole_real_line"; intervals <- list(list(lower=NULL,upper=NULL))
      } else {
        kind <- "empty"; intervals <- list()
      }
    } else if (discriminant == 0) {
      if (A < 0) {
        kind <- "whole_real_line"; intervals <- list(list(lower=NULL,upper=NULL))
      } else {
        value <- -B/(2*A)
        kind <- "isolated_point"; intervals <- list(list(lower=value,upper=value))
      }
    } else {
      signed_root <- if (B >= 0) sqrt(discriminant) else -sqrt(discriminant)
      q <- -(B+signed_root)/2
      roots <- sort(c(q/A,C/q))
      if (A > 0) {
        kind <- "bounded_interval"; intervals <- list(list(lower=roots[1L],upper=roots[2L]))
      } else {
        kind <- "two_rays"
        intervals <- list(list(lower=NULL,upper=roots[1L]),list(lower=roots[2L],upper=NULL))
      }
    }
  }
  zero_inside <- if (length(intervals)) any(vapply(intervals,function(interval) {
    (is.null(interval$lower) || interval$lower <= 0) &&
      (is.null(interval$upper) || interval$upper >= 0)
  },logical(1))) else FALSE
  list(kind=kind,intervals=intervals,quadratic_coefficients=c(A,B,C),contains_zero=zero_inside)
}

ar_set <- function(reduced,first,variance_reduced,variance_first,covariance,critical) {
  if (variance_reduced < 0 || variance_first < 0 ||
      variance_reduced*variance_first-covariance^2 < 0) stop("Non-PSD two-coordinate covariance")
  quadratic_set(first^2-critical*variance_first,
                -2*reduced*first+2*critical*covariance,
                reduced^2-critical*variance_reduced)
}

benchmarks <- list(one_year=c(1,0),slope_1y_3m=c(1,-1),
                   three_month=c(0,1),forward_3m_1y=c(4/3,-1/3))
outcome_names <- c("manufacturing","industrial","durability_contrast")

fit_case <- function(h=12L,p=2L,bandwidth=NULL) {
  D <- design(h,p);X <- cbind(D$Z,D$W);n <- nrow(X);k <- ncol(X)
  F <- qr_fit(X,cbind(D$responses,D$financial))
  coefficient <- as.numeric(F$beta[1L,])
  # Each of the five equations retains its own residual. No n factor added.
  score <- F$residual*F$operator[,1L]
  base <- ceiling(4*(n/100)^(2/9))
  L <- if (is.null(bandwidth)) (if (h < 0) 11L else h)+base else bandwidth
  V <- calendar_covariance(score,D$dates,L,k)
  critical_family <- qnorm(1-.05/8)^2
  critical_individual <- qnorm(.975)^2
  outcomes <- list()
  for (j in seq_along(outcome_names)) {
    reduced <- coefficient[j]; vr <- V[j,j]
    p_reduced <- 2*pnorm(-abs(reduced)/sqrt(vr))
    fits <- list()
    for (name in names(benchmarks)) {
      weights <- benchmarks[[name]]
      first <- sum(weights*coefficient[4:5])
      vf <- as.numeric(crossprod(weights,V[4:5,4:5] %*% weights))
      cross <- sum(V[j,4:5]*weights)
      family <- ar_set(reduced,first,vr,vf,cross,critical_family)
      individual <- ar_set(reduced,first,vr,vf,cross,critical_individual)
      point <- if (first == 0) NULL else reduced/first
      delta_se <- NULL
      if (first != 0) {
        gradient <- c(1/first,-reduced/first^2)
        pair <- matrix(c(vr,cross,cross,vf),2,2)
        delta_se <- sqrt(as.numeric(crossprod(gradient,pair %*% gradient)))
      }
      if (family$contains_zero != (p_reduced >= .05/4)) stop("Zero restriction equivalence fails")
      fits[[name]] <- list(first_stage=first,first_stage_variance=vf,
                          reduced_first_covariance=cross,ratio_point=point,
                          diagnostic_delta_se=delta_se,family_AR95=family,individual_AR95=individual)
    }
    outcomes[[outcome_names[j]]] <- list(reduced_form=reduced,reduced_form_se=sqrt(vr),
                                        reduced_form_p=p_reduced,benchmarks=fits)
  }
  residual_x <- qr_fit(D$W,D$financial[,1L])$residual[,1L]
  residual_z <- qr_fit(D$W,D$Z)$residual[,1L]
  list(horizon=h,lags=p,n=n,columns=k,residual_df=n-k,bandwidth=L,
       first="2005-01",last="2016-01",coefficient_order=c(outcome_names,"yield_1y","yield_3m"),
       coefficients=coefficient,joint_covariance=V,
       family_alpha_per_normalisation=.05/4,family_critical_square=critical_family,
       maximum_leverage=max(F$leverage),
       first_stage_1y=list(coefficient=coefficient[4L],se=sqrt(V[4L,4L]),
                           hac_t_squared=coefficient[4L]^2/V[4L,4L],partial_r_squared=cor(residual_x,residual_z)^2),
       outcomes=outcomes)
}

primary <- fit_case()
profiles <- lapply(c(0L,6L,12L,18L,24L),function(h) fit_case(h))
base <- primary$bandwidth-12L
sensitivity <- list(list(case="three_lags",result=fit_case(p=3L)),
                     list(case="short_bandwidth",result=fit_case(bandwidth=12L+ceiling(base/2))),
                     list(case="long_bandwidth",result=fit_case(bandwidth=12L+2L*base)))
predetermined <- fit_case(h=-1L)
D <- design();X <- cbind(D$Z,D$W)
deletions <- lapply(seq_len(nrow(X)),function(i) {
  F <- qr_fit(X[-i,,drop=FALSE],cbind(D$responses[-i,1L],D$financial[-i,1L]))
  reduced <- F$beta[1L,1L];first <- F$beta[1L,2L]
  list(deleted_origin=month_name(D$dates[i]),reduced_form=reduced,first_stage=first,
       ratio=if (first == 0) NULL else reduced/first)
})

records <- list()
emit <- function(path,value,type) {
  if (type == "number") value <- format(value,digits=17,scientific=TRUE,trim=TRUE)
  else if (type == "logical") value <- if (value) "true" else "false"
  else if (type == "null") value <- ""
  records[[length(records)+1L]] <<- data.frame(quantity=path,value=as.character(value),type=type,
                                            stringsAsFactors=FALSE)
}
flatten <- function(value,path) {
  if (is.null(value)) {
    emit(path,NULL,"null")
  } else if (is.matrix(value)) {
    for (i in seq_len(nrow(value))) for (j in seq_len(ncol(value))) {
      emit(paste(path,i-1L,j-1L,sep="."),value[i,j],"number")
    }
  } else if (is.list(value)) {
    if (length(value)) {
      labels <- names(value)
      for (i in seq_along(value)) {
        label <- if (is.null(labels)) as.character(i-1L) else labels[i]
        flatten(value[[i]],paste(path,label,sep="."))
      }
    }
  } else if (length(value) > 1L) {
    for (i in seq_along(value)) flatten(value[i],paste(path,i-1L,sep="."))
  } else if (is.numeric(value)) emit(path,value,"number")
  else if (is.logical(value)) emit(path,value,"logical")
  else if (is.character(value)) emit(path,value,"string")
  else stop("Unsupported output type")
}
flatten(primary,"primary");flatten(profiles,"profiles");flatten(sensitivity,"sensitivity")
flatten(predetermined,"predetermined");flatten(deletions,"single_origin_deletions")
output <- do.call(rbind,records)
if (anyDuplicated(output$quantity)) stop("Repeated output quantity")
dir.create(dirname(args[2L]),recursive=TRUE,showWarnings=FALSE)
write.csv(output,args[2L],row.names=FALSE,na="")
cat("Independent future-policy quantities written:",nrow(output),"\n")
