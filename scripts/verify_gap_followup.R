#!/usr/bin/env Rscript
# Verify a post-estimation point-null test and joint-ellipse product bounds.
# Usage: Rscript verify_gap_followup.R ESTIMATES_CSV OUTPUT_CSV
# No outcome regressions or additional packages are used.

ellipse_product_bounds <- function(weight, theta, V) {
  if (!identical(dim(V), c(2L, 2L)) || any(!is.finite(V)) ||
      any(diag(V) <= 0) || V[1L, 2L] != V[2L, 1L]) {
    stop("Invalid joint covariance")
  }
  marginal_product <- sqrt(V[1L, 1L]) * sqrt(V[2L, 2L])
  if (!is.finite(marginal_product) || marginal_product <= 0 ||
      abs(V[1L, 2L]) >= marginal_product) {
    stop("Singular or non-positive-definite joint covariance")
  }
  lower <- tryCatch(t(chol(V)), error = function(e) {
    stop("Joint covariance Cholesky factorisation failed: ", conditionMessage(e))
  })
  reconstruction_error <- max(abs(tcrossprod(lower) - V))
  if (reconstruction_error > 100 * .Machine$double.eps * max(abs(V))) {
    stop("Covariance factorisation reconstruction failed")
  }
  radius <- sqrt(stats::qchisq(0.95, df = 2L))
  centre <- c(weight, theta)
  boundary_product <- function(angle) {
    point <- centre + radius * as.vector(lower %*% c(cos(angle), sin(angle)))
    value <- prod(point)
    if (any(!is.finite(point)) || !is.finite(value)) stop("Nonfinite ellipse product")
    value
  }
  knots <- seq(0, 2 * pi, length.out = 65L)
  # The product extrema on a nondegenerate ellipse occur on its boundary.
  # Optimise each short arc in both directions and retain every arc endpoint.
  candidates <- vapply(knots, boundary_product, numeric(1L))
  for (i in seq_len(64L)) {
    interval <- knots[c(i, i + 1L)]
    low <- stats::optimize(boundary_product, interval, maximum = FALSE, tol = 1e-12)
    high <- stats::optimize(boundary_product, interval, maximum = TRUE, tol = 1e-12)
    candidates <- c(candidates, low$objective, high$objective,
                    boundary_product(low$minimum), boundary_product(high$maximum))
  }
  bounds <- range(candidates)
  # A separate dense-grid and centre check catches missed extrema or arc errors.
  grid_values <- vapply(seq(0, 2 * pi, length.out = 4097L),
                        boundary_product, numeric(1L))
  tolerance <- 1e-10 * max(1, abs(bounds), abs(grid_values), abs(prod(centre)))
  if (bounds[1L] > min(grid_values) + tolerance ||
      bounds[2L] < max(grid_values) - tolerance ||
      bounds[1L] > prod(centre) + tolerance ||
      bounds[2L] < prod(centre) - tolerance || bounds[1L] >= bounds[2L]) {
    stop("Ellipse extrema candidate validation failed")
  }
  setNames(bounds, c("ellipse95_low", "ellipse95_high"))
}

canonical_estimates <- function(input) {
  canonical_columns <- c("weight", "weight_se", "theta", "theta_se",
                         "covariance_weight_theta")
  independent_columns <- c("w", "se_w", "theta", "se_theta", "cov_w_theta")
  if (all(canonical_columns %in% names(input))) {
    names_to_use <- canonical_columns
  } else if (all(independent_columns %in% names(input))) {
    names_to_use <- independent_columns
  } else {
    stop("Input lacks a supported joint-estimate column schema")
  }
  if (!all(c("case", "n", "first", "last") %in% names(input))) {
    stop("Input lacks case or sample fields")
  }
  aliases <- c(primary_h12 = "primary", lag6_h12 = "six_lags",
               poor_man_h12 = "poor_man", pre_covid_h12 = "pre_pandemic",
               primary_short_h12 = "short_bandwidth",
               primary_long_h12 = "long_bandwidth")
  cases <- c("primary", "six_lags", "poor_man", "pre_pandemic",
             "short_bandwidth", "long_bandwidth")
  labels <- as.character(input$case)
  alias_rows <- labels %in% names(aliases)
  labels[alias_rows] <- unname(aliases[labels[alias_rows]])
  keep <- labels %in% cases
  input <- input[keep, , drop = FALSE]
  labels <- labels[keep]
  if (anyDuplicated(labels) || !setequal(labels, cases)) {
    stop("Exactly one row is required for each of the six declared cases")
  }
  order <- match(cases, labels)
  input <- input[order, , drop = FALSE]
  result <- data.frame(case = cases, n = input$n, stringsAsFactors = FALSE)
  for (i in seq_along(canonical_columns)) {
    result[[canonical_columns[i]]] <- suppressWarnings(as.numeric(input[[names_to_use[i]]]))
  }
  result$n <- suppressWarnings(as.numeric(result$n))
  if (any(!is.finite(as.matrix(result[, setdiff(names(result), "case")])))) {
    stop("Nonfinite or nonnumeric selected input")
  }
  expected_n <- ifelse(cases == "pre_pandemic", 228L, 308L)
  expected_last <- ifelse(cases == "pre_pandemic", "2018-12", "2025-08")
  if (any(result$n != expected_n) || any(input$first != "2000-01") ||
      any(input$last != expected_last)) stop("Declared follow-up sample differs from retained cases")
  horizon_column <- if ("horizon" %in% names(input)) "horizon" else if ("h" %in% names(input)) "h" else NULL
  if (is.null(horizon_column) || any(input[[horizon_column]] != 12L)) {
    stop("Follow-up requires the retained twelve-month cases")
  }
  if (any(result$weight_se <= 0) || any(result$theta_se <= 0)) {
    stop("Nondegenerate positive marginal standard errors are required")
  }
  result
}

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) != 2L) {
    stop("Usage: Rscript verify_gap_followup.R ESTIMATES_CSV OUTPUT_CSV")
  }
  input_path <- normalizePath(args[1L], mustWork = TRUE)
  output_path <- args[2L]
  if (normalizePath(output_path, mustWork = FALSE) == input_path) {
    stop("The output must not overwrite the retained estimates")
  }
  supplied <- read.csv(input_path, stringsAsFactors = FALSE, check.names = FALSE,
                       na.strings = c("", "NA"))
  estimates <- canonical_estimates(supplied)
  result <- do.call(rbind, lapply(seq_len(nrow(estimates)), function(i) {
    row <- estimates[i, ]
    p_weight <- 2 * stats::pnorm(-abs(row$weight / row$weight_se))
    p_theta <- 2 * stats::pnorm(-abs(row$theta / row$theta_se))
    V <- matrix(c(row$weight_se^2, row$covariance_weight_theta,
                  row$covariance_weight_theta, row$theta_se^2), nrow = 2L)
    bounds <- ellipse_product_bounds(row$weight, row$theta, V)
    values <- c(p_weight, p_theta, max(p_weight, p_theta), bounds)
    if (any(!is.finite(values)) || any(values[1:3] < 0 | values[1:3] > 1)) {
      stop("Nonfinite probability or product bound")
    }
    data.frame(case = row$case, n = row$n, p_weight = p_weight,
               p_theta = p_theta, p_IUT = max(p_weight, p_theta),
               ellipse95_low = unname(bounds[1L]),
               ellipse95_high = unname(bounds[2L]),
               stringsAsFactors = FALSE, check.names = FALSE)
  }))
  expected <- c("case", "n", "p_weight", "p_theta", "p_IUT",
                "ellipse95_low", "ellipse95_high")
  if (!identical(names(result), expected)) stop("Follow-up output schema mismatch")
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  # Preserve seventeen significant digits for cross-language comparison.
  formatted <- result
  for (name in setdiff(names(formatted), "case")) {
    formatted[[name]] <- sprintf("%.17g", result[[name]])
  }
  write.table(formatted, output_path, sep = ",", quote = FALSE,
              row.names = FALSE, col.names = TRUE, na = "")
  cat("Six follow-up cases written to", normalizePath(output_path), "\n")
}

main()
