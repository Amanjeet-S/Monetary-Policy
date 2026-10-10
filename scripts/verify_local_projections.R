#!/usr/bin/env Rscript
# Selected local-projection checks using standard R only.
# Usage: Rscript verify_local_projections.R REPOSITORY [OUTPUT_CSV]

month_number <- function(x) {
  if (any(!grepl("^[0-9]{4}-[0-9]{2}$", x))) stop("Invalid monthly date")
  year <- as.integer(substr(x, 1L, 4L))
  month <- as.integer(substr(x, 6L, 7L))
  if (any(month < 1L | month > 12L)) stop("Invalid month number")
  12L * year + month - 1L
}

qr_fit <- function(X, Y) {
  X <- as.matrix(X)
  Y <- as.matrix(Y)
  n <- nrow(X)
  k <- ncol(X)
  if (nrow(Y) != n || any(!is.finite(X)) || any(!is.finite(Y))) {
    stop("Invalid regression input")
  }
  decomposition <- qr(X, tol = 1e-10, LAPACK = FALSE)
  if (decomposition$rank != k || n <= k) stop("Rank or degrees-of-freedom failure")
  Q <- qr.Q(decomposition, complete = FALSE)
  R <- qr.R(decomposition, complete = FALSE)
  pivot <- decomposition$pivot
  coefficients <- matrix(0, k, ncol(Y),
                         dimnames = list(colnames(X), colnames(Y)))
  coefficients[pivot, ] <- backsolve(R, crossprod(Q, Y))
  residuals <- Y - X %*% coefficients
  # Each loading row is x_t'(X'X)^(-1), returned in original column order.
  loadings <- matrix(0, n, k, dimnames = list(NULL, colnames(X)))
  loadings[, pivot] <- Q %*% t(backsolve(R, diag(k)))
  if (any(!is.finite(coefficients)) || any(!is.finite(residuals)) ||
      any(!is.finite(loadings))) stop("Nonfinite QR result")
  list(coefficients = coefficients, residuals = residuals,
       loadings = loadings, rank = k)
}

calendar_hac <- function(influences, calendar, L, k_full) {
  n <- nrow(influences)
  if (length(calendar) != n || any(diff(calendar) <= 0L) ||
      any(!is.finite(influences)) || L < 0L || L != as.integer(L) || n <= k_full) {
    stop("Invalid covariance input")
  }
  covariance <- crossprod(influences)
  for (i in seq_len(n - 1L)) {
    distance <- calendar - calendar[i]
    later <- which(distance > 0L & distance <= L)
    if (length(later)) {
      weighted <- colSums(influences[later, , drop = FALSE] *
                          (1 - distance[later] / (L + 1)))
      term <- tcrossprod(influences[i, ], weighted)
      covariance <- covariance + term + t(term)
    }
  }
  covariance <- covariance * n / (n - k_full)
  if (any(!is.finite(covariance))) stop("Nonfinite covariance estimate")
  (covariance + t(covariance)) / 2
}

selected_check <- function(panel, calendar, case) {
  at <- function(x, t) x[match(t, calendar)]
  D <- panel$durable_index
  N <- panel$nondurable_index
  P <- panel$hicp_index
  gD <- 100 * log(D / at(D, calendar - 1L))
  gN <- 100 * log(N / at(N, calendar - 1L))
  inflation <- 100 * log(P / at(P, calendar - 12L))
  policy <- panel[[paste0("shock_MP_", case$family)]] / 0.10
  information <- panel[[paste0("shock_CBI_", case$family)]] / 0.10
  dates <- seq.int(month_number(case$first), month_number(case$last))
  Z <- cbind(intercept = rep(1, length(dates)),
             vapply(2:12, function(j) as.numeric(dates %% 12L + 1L == j),
                    numeric(length(dates))))
  colnames(Z)[2:12] <- paste0("month", 2:12)
  for (j in seq_len(case$p)) {
    lagged <- cbind(at(gD, dates - j), at(gN, dates - j),
                    at(inflation, dates - j), at(policy, dates - j), at(information, dates - j))
    colnames(lagged) <- paste0("L", j, "_", c("Dgrowth", "Ngrowth", "inflation", "m", "c"))
    Z <- cbind(Z, lagged)
  }
  current_m <- at(policy, dates)
  current_c <- at(information, dates)
  F <- cbind(Z, m = current_m, c = current_c)
  R <- cbind(Z, r = current_m + current_c)
  levels <- cbind(at(D, dates - 1L), at(N, dates - 1L),
                  at(D, dates + case$h), at(N, dates + case$h))
  if (any(!is.finite(F)) || any(!is.finite(levels)) || any(levels <= 0)) {
    stop(paste("Missing or invalid required observation in", case$name,
               "with exact calendar bounds; no rows were removed"))
  }
  if (qr(Z, tol = 1e-10, LAPACK = FALSE)$rank != ncol(Z)) stop("Control rank failure")
  durable <- 100 * log(levels[, 3L] / levels[, 1L])
  nondurable <- 100 * log(levels[, 4L] / levels[, 2L])
  relative <- 100 * (log(levels[, 3L] / levels[, 4L]) -
                     log(levels[, 1L] / levels[, 2L]))
  fit_F <- qr_fit(F, cbind(relative = relative, durable = durable, nondurable = nondurable))
  fit_R <- qr_fit(R, cbind(relative = relative))
  fit_W <- qr_fit(R, cbind(c = current_c))
  beta_m <- fit_F$coefficients["m", "relative"]
  beta_c <- fit_F$coefficients["c", "relative"]
  gamma <- fit_R$coefficients["r", "relative"]
  weight <- fit_W$coefficients["r", "c"]
  theta <- beta_c - beta_m
  gap <- gamma - beta_m
  beta_D <- fit_F$coefficients["m", "durable"]
  beta_N <- fit_F$coefficients["m", "nondurable"]
  if (any(!is.finite(c(beta_m, beta_c, gamma, weight, theta, gap, beta_D, beta_N)))) {
    stop("Nonfinite selected projection quantity")
  }
  influences <- cbind(
    beta_m = fit_F$loadings[, "m"] * fit_F$residuals[, "relative"],
    beta_c = fit_F$loadings[, "c"] * fit_F$residuals[, "relative"],
    gamma = fit_R$loadings[, "r"] * fit_R$residuals[, "relative"],
    w = fit_W$loadings[, "r"] * fit_W$residuals[, "c"],
    beta_D = fit_F$loadings[, "m"] * fit_F$residuals[, "durable"],
    beta_N = fit_F$loadings[, "m"] * fit_F$residuals[, "nondurable"])
  if (abs(gap - weight * theta) > 1e-8 * max(1, abs(gap)) ||
      abs(beta_m - (beta_D - beta_N)) > 1e-8 * max(1, abs(beta_m))) {
    stop("Projection identity check failed")
  }
  IF_delta <- influences[, "gamma"] - influences[, "beta_m"]
  IF_theta <- influences[, "beta_c"] - influences[, "beta_m"]
  product_IF <- weight * IF_theta + theta * influences[, "w"]
  IF_identity_error <- max(abs(IF_delta - product_IF))
  if (!is.finite(IF_identity_error) ||
      IF_identity_error > 1e-8 * max(1, abs(IF_delta), abs(product_IF))) {
    stop("Per-observation gap influence identity check failed")
  }
  n <- length(dates)
  B <- ceiling(4 * (n / 100)^(2 / 9))
  offset <- switch(case$bandwidth, standard = B, short = ceiling(B / 2), long = 2 * B)
  if (is.null(offset)) stop("Unknown bandwidth convention")
  L <- case$h + offset
  V <- calendar_hac(influences, dates, L, fit_F$rank)
  variance <- function(a) {
    value <- as.numeric(crossprod(a, V %*% a))
    if (!is.finite(value)) stop("Nonfinite covariance quadratic form")
    if (value < -1e-10 * max(1e-12, max(diag(V)))) stop("Negative covariance quadratic form")
    max(value, 0)
  }
  se_m <- sqrt(variance(c(1, 0, 0, 0, 0, 0)))
  se_c <- sqrt(variance(c(0, 1, 0, 0, 0, 0)))
  se_gamma <- sqrt(variance(c(0, 0, 1, 0, 0, 0)))
  se_w <- sqrt(variance(c(0, 0, 0, 1, 0, 0)))
  se_theta <- sqrt(variance(c(-1, 1, 0, 0, 0, 0)))
  se_gap <- sqrt(variance(c(-1, 0, 1, 0, 0, 0)))
  se_D <- sqrt(variance(c(0, 0, 0, 0, 1, 0)))
  se_N <- sqrt(variance(c(0, 0, 0, 0, 0, 1)))
  if (any(!is.finite(c(beta_m, beta_c, gamma, weight, theta, gap, beta_D, beta_N,
                       se_m, se_c, se_gamma, se_w, se_theta, se_gap, se_D, se_N)))) {
    stop("Nonfinite selected estimate or standard error")
  }
  if (se_w <= 0 || se_theta <= 0) {
    stop("The prescribed joint-normal product rectangle requires nondegenerate marginal uncertainty")
  }
  sector_difference_variance <- variance(c(0, 0, 0, 0, 1, -1))
  if (abs(sector_difference_variance - se_m^2) > 1e-8 * max(1, se_m^2)) {
    stop("Joint sector covariance check failed")
  }
  z <- stats::qnorm(0.975)
  z_joint <- stats::qnorm(0.9875)
  w_bounds <- weight + c(-1, 1) * z_joint * se_w
  theta_bounds <- theta + c(-1, 1) * z_joint * se_theta
  products <- as.vector(outer(w_bounds, theta_bounds))
  if (any(!is.finite(c(w_bounds, theta_bounds, products))) ||
      w_bounds[1L] >= w_bounds[2L] || theta_bounds[1L] >= theta_bounds[2L]) {
    stop("Nonfinite or numerically degenerate product-interval bounds")
  }
  data.frame(case = case$name, family = case$family, p = case$p, h = case$h,
    bandwidth = case$bandwidth, n = n, first = case$first, last = case$last,
    k_F = fit_F$rank, k_R = fit_R$rank, k_W = fit_W$rank, B = B, L = L,
    finite_sample_factor = n / (n - fit_F$rank), shock_unit_pp = 0.10,
    beta_m = beta_m, beta_c = beta_c, gamma = gamma, w = weight,
    theta = theta, delta = gap, product_delta = weight * theta,
    max_if_delta_identity_error = IF_identity_error,
    se_beta_m = se_m, se_beta_c = se_c, se_gamma = se_gamma, se_w = se_w,
    se_theta = se_theta, se_delta = se_gap,
    cov_beta_m_delta = V[1L, 3L] - V[1L, 1L],
    cov_w_theta = V[4L, 2L] - V[4L, 1L],
    beta_m_lo = beta_m - z * se_m, beta_m_hi = beta_m + z * se_m,
    beta_c_lo = beta_c - z * se_c, beta_c_hi = beta_c + z * se_c,
    gamma_lo = gamma - z * se_gamma, gamma_hi = gamma + z * se_gamma,
    w_lo = weight - z * se_w, w_hi = weight + z * se_w,
    theta_lo = theta - z * se_theta, theta_hi = theta + z * se_theta,
    delta_lo = gap - z * se_gap, delta_hi = gap + z * se_gap,
    product_gap_lo = min(products), product_gap_hi = max(products),
    joint_w_lo = w_bounds[1L], joint_w_hi = w_bounds[2L],
    joint_theta_lo = theta_bounds[1L], joint_theta_hi = theta_bounds[2L],
    beta_D = beta_D, beta_N = beta_N, se_beta_D = se_D, se_beta_N = se_N,
    cov_beta_D_beta_N = V[5L, 6L],
    se_relative_from_sector_cov = sqrt(sector_difference_variance),
    stringsAsFactors = FALSE, check.names = FALSE)
}

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) < 1L || length(args) > 2L) {
    stop("Usage: Rscript verify_local_projections.R REPOSITORY [OUTPUT_CSV]")
  }
  repository <- normalizePath(args[1L], mustWork = TRUE)
  script_flag <- grep("^--file=", commandArgs(), value = TRUE)
  script_directory <- if (length(script_flag)) dirname(normalizePath(sub("^--file=", "", script_flag[1L]))) else getwd()
  output <- if (length(args) == 2L) args[2L] else file.path(script_directory, "r_selected_checks.csv")
  panel <- read.csv(file.path(repository, "data/processed/monthly_panel.csv"),
                    stringsAsFactors = FALSE, na.strings = c("", "NA"), check.names = FALSE)
  required <- c("month", "durable_index", "nondurable_index", "hicp_index",
                "shock_MP_median", "shock_CBI_median", "shock_MP_pm", "shock_CBI_pm")
  if (!all(required %in% names(panel))) stop("Required input fields absent")
  calendar <- month_number(panel$month)
  if (any(diff(calendar) != 1L)) stop("Input must contain a unique ordered monthly calendar")
  for (name in setdiff(required, "month")) {
    supplied <- panel[[name]]
    converted <- suppressWarnings(as.numeric(supplied))
    if (any(is.nan(converted)) || any(is.infinite(converted)) ||
        any(is.na(converted) & !is.na(supplied))) stop("Invalid supplied numeric value")
    panel[[name]] <- converted
  }
  for (name in c("durable_index", "nondurable_index", "hicp_index")) {
    if (any(panel[[name]] <= 0, na.rm = TRUE)) stop("Nonpositive observed index")
  }
  case <- function(name, p = 12L, h = 12L, last = "2025-08",
                   family = "median", bandwidth = "standard") {
    list(name = name, p = p, h = h, first = "2000-01", last = last,
         family = family, bandwidth = bandwidth)
  }
  cases <- list(case("primary_h12"), case("lag6_h12", p = 6L),
                case("poor_man_h12", family = "pm"),
                case("pre_covid_h12", last = "2018-12"),
                case("common_path_h0", h = 0L, last = "2024-08"),
                case("common_path_h12", last = "2024-08"),
                case("common_path_h24", h = 24L, last = "2024-08"),
                case("primary_short_h12", bandwidth = "short"),
                case("primary_long_h12", bandwidth = "long"))
  results <- do.call(rbind, lapply(cases, function(x) selected_check(panel, calendar, x)))
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  write.csv(results, output, row.names = FALSE, na = "")
  cat("Selected checks written to", normalizePath(output), "\n")
}

main()
