#!/usr/bin/env Rscript
# Independent event-rotation and conditional-envelope checks using standard R.

main <- function() {
  args <- commandArgs(trailingOnly=TRUE)
  if(length(args)!=2L) stop('Usage: Rscript verify_rotation_sensitivity.R ROOT OUTPUT_CSV')
  flag <- grep('^--file=',commandArgs(),value=TRUE)
  directory <- dirname(normalizePath(sub('^--file=','',flag[1])))
  source(file.path(directory,'verify_joint_stability.R'))
  root <- normalizePath(args[1],mustWork=TRUE)
  events <- read.csv(file.path(root,'data/raw/2026-10-10/jk_ecb_events.csv'),stringsAsFactors=FALSE)
  event_matrix <- cbind(events$pc1,events$STOXX50)
  decomposition <- qr(event_matrix,tol=1e-12,LAPACK=FALSE)
  if(decomposition$rank!=2L || any(decomposition$pivot!=1:2) || nrow(events)!=312L) stop('Unexpected retained event design')
  Q <- qr.Q(decomposition); R <- qr.R(decomposition)
  S <- diag(sign(diag(R))); Q <- Q%*%S; R <- S%*%R
  lower <- if(R[1,2]>0) atan(R[1,2]/R[2,2]) else 0
  upper <- if(R[1,2]>=0) pi/2 else atan2(R[2,2],-R[1,2])
  if(upper>=pi/2) stop('Unbounded endpoint needs a separate analytic implementation')
  median_angle <- (lower+upper)/2
  ca <- cos(median_angle); sa <- sin(median_angle)
  rotation <- matrix(c(ca,-sa,sa,ca),2,2)
  median <- Q%*%rotation%*%diag(c(R[1,1]*ca,R[1,1]*sa))
  rounded_error <- max(abs(round(median,8)-cbind(events$MP_median,events$CBI_median)))
  if(rounded_error>1e-12) stop('Retained median does not reproduce')
  event_v <- Q[,2]*R[1,1]
  panel <- read.csv(file.path(root,'data/processed/monthly_panel.csv'),stringsAsFactors=FALSE,na.strings=c('','NA'))
  event_months <- substr(events$date,1,7)
  active <- panel$month>=min(event_months) & panel$month<=max(event_months)
  monthly_rate <- monthly_v <- rep(NA_real_,nrow(panel))
  monthly_rate[active] <- monthly_v[active] <- 0
  for(i in seq_len(nrow(events))) {
    j <- match(event_months[i],panel$month)
    monthly_rate[j] <- monthly_rate[j]+events$pc1[i]
    monthly_v[j] <- monthly_v[j]+event_v[i]
  }
  panel$shock_MP_median <- monthly_rate
  panel$shock_CBI_median <- monthly_v
  d <- make_design(panel,'2025-08')
  kZ <- ncol(d$Z)
  F <- fit_qr(cbind(d$Z,d$m,d$c),d$Y)
  Reduced <- fit_qr(cbind(d$Z,d$m),d$Y)
  K <- fit_qr(cbind(d$Z,d$m),d$c)
  b_rate <- F$b[kZ+1]; b_v <- F$b[kZ+2]
  gamma <- Reduced$b[kZ+1]; kappa <- K$b[kZ+1]
  I <- cbind(F$loading[,kZ+1]*F$e,F$loading[,kZ+2]*F$e,
             Reduced$loading[,kZ+1]*Reduced$e,Reduced$loading[,kZ+1]*K$e)*sqrt(F$n/(F$n-F$k))
  V <- hac(I,d$dates,18)
  if(abs(gamma-b_rate-b_v*kappa)>1e-8) stop('Invariant mixture identity failure')
  covariance <- V[1:3,1:3]
  if(min(eigen(covariance,symmetric=TRUE,only.values=TRUE)$values)<=0) stop('Nondegenerate covariance required')
  critical <- sqrt(qchisq(.95,3))
  coefficients <- c(b_rate,b_v,gamma)
  at_endpoint <- function(angle) {
    policy <- c(1,-tan(angle),0); gap <- c(-1,tan(angle),1)
    beta <- sum(policy*coefficients); delta <- sum(gap*coefficients)
    beta_se <- sqrt(drop(t(policy)%*%covariance%*%policy))
    delta_se <- sqrt(drop(t(gap)%*%covariance%*%gap))
    c(beta_m=beta,delta=delta,beta_m_se=beta_se,delta_se=delta_se,
      beta_m_joint_low=beta-critical*beta_se,beta_m_joint_high=beta+critical*beta_se,
      delta_joint_low=delta-critical*delta_se,delta_joint_high=delta+critical*delta_se)
  }
  endpoints <- rbind(at_endpoint(lower),at_endpoint(upper))
  values <- c('source.qr_positive_diagonal.0.0'=R[1,1],
      'source.qr_positive_diagonal.0.1'=R[1,2],
      'source.qr_positive_diagonal.1.1'=R[2,2],
      'source.angle_lower_radians'=lower,'source.angle_upper_radians'=upper,
      'source.median_radians'=median_angle,'source.rounded_median_max_abs_error'=rounded_error,
      'basis.b_rate'=b_rate,'basis.b_orthogonal'=b_v,'basis.gamma'=gamma,
      'basis.kappa'=kappa,'basis.joint_critical'=critical)
  for(i in 1:4) for(j in 1:4) values[paste0('basis.covariance_with_kappa.',i-1,'.',j-1)] <- V[i,j]
  for(i in 1:2) for(key in colnames(endpoints)) values[paste0('endpoint_limits.',i-1,'.',key)] <- endpoints[i,key]
  for(name in c('beta_m','delta')) {
    values[paste0('envelopes.',name,'.point_set_infimum')] <- min(endpoints[,name])
    values[paste0('envelopes.',name,'.point_set_supremum')] <- max(endpoints[,name])
    values[paste0('envelopes.',name,'.conditional_joint_envelope_low')] <- min(endpoints[,paste0(name,'_joint_low')])
    values[paste0('envelopes.',name,'.conditional_joint_envelope_high')] <- max(endpoints[,paste0(name,'_joint_high')])
  }
  theta_p <- 2*pnorm(-abs(b_v/sqrt(V[2,2])))
  weight_p_lower <- 2*pnorm(-abs((tan(lower)+kappa)/sqrt(V[4,4])))
  weight_p_upper <- 2*pnorm(-abs((tan(upper)+kappa)/sqrt(V[4,4])))
  if(-kappa>=tan(lower) && -kappa<=tan(upper)) p_sup <- 1 else p_sup <- max(theta_p,weight_p_lower,weight_p_upper)
  values['theta_p_all_interior_rotations'] <- theta_p
  values['iut_p_supremum_on_strict_interval'] <- p_sup
  primitive <- c(b_rate,b_v,kappa)
  primitive_V <- V[c(1,2,4),c(1,2,4)]
  rectangle_critical <- qnorm(1-.05/6)
  primitive_bounds <- cbind(primitive-rectangle_critical*sqrt(diag(primitive_V)),primitive+rectangle_critical*sqrt(diag(primitive_V)))
  policy_values <- gap_values <- numeric(0)
  for(x in tan(c(lower,upper))) {
    for(br in primitive_bounds[1,]) for(bv in primitive_bounds[2,]) policy_values <- c(policy_values,br-x*bv)
    for(bv in primitive_bounds[2,]) for(kap in primitive_bounds[3,]) gap_values <- c(gap_values,(x+kap)*bv)
  }
  values['conservative_primitive_rectangle.critical'] <- rectangle_critical
  for(i in 1:3) for(j in 1:2) values[paste0('conservative_primitive_rectangle.bounds.',i-1,'.',j-1)] <- primitive_bounds[i,j]
  values['conservative_primitive_rectangle.beta_m_envelope_low'] <- min(policy_values)
  values['conservative_primitive_rectangle.beta_m_envelope_high'] <- max(policy_values)
  values['conservative_primitive_rectangle.delta_envelope_low'] <- min(gap_values)
  values['conservative_primitive_rectangle.delta_envelope_high'] <- max(gap_values)
  dir.create(dirname(args[2]),recursive=TRUE,showWarnings=FALSE)
  write.csv(data.frame(key=names(values),value=as.numeric(values)),args[2],row.names=FALSE)
  cat('Independent rotation invariants and envelopes written.\n')
}

main()
