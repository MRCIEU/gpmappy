# Generate the gpmapr side of the gpmappy parity contract.
#
# Loads the gpmapr R sources (without running .onLoad, so no network access), mocks
# httr::GET/POST/DELETE so every request is served from fixtures, runs each scenario
# in tests/contract/scenarios.json and writes:
#
#   <output_dir>/surface.json        exported functions, their formals and supported API versions
#   <output_dir>/fixtures/           a copy of gpmapr's recorded API fixtures (tests/testthat/fixtures)
#   <output_dir>/golden/<id>.json    requests made + normalized result/error/warnings
#
# Scenarios run against one of two fixture sets:
#   "gpmapr"  gpmapr's own recorded responses, served by the URLs in their index.json
#   "edge"    gpmappy's hand-built edge cases, served by tests/contract/fixtures/routes.json
#
# Usage (from anywhere):
#   Rscript scripts/parity/generate_gpmapr_contract.R [path/to/gpmapr] [output_dir]
#
# The gpmapr path defaults to $GPMAPR_PATH, then ../gpmapr next to this repository, and
# the output directory to tests/contract/gpmapr.

suppressPackageStartupMessages({
  library(jsonlite)
  library(httr)
  library(testthat)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_dir <- dirname(normalizePath(sub("^--file=", "", script_arg[[1]])))
repo_root <- normalizePath(file.path(script_dir, "..", ".."))
contract_dir <- file.path(repo_root, "tests", "contract")
edge_dir <- file.path(contract_dir, "fixtures")
source(file.path(script_dir, "normalize.R"))

args <- commandArgs(trailingOnly = TRUE)
gpmapr_path <- if (length(args) >= 1) args[[1]] else Sys.getenv("GPMAPR_PATH", file.path(dirname(repo_root), "gpmapr"))
out_dir <- if (length(args) >= 2) args[[2]] else file.path(contract_dir, "gpmapr")
gpmapr_path <- normalizePath(gpmapr_path, mustWork = TRUE)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

base_url <- "https://gpmap.fixture.test/api"

gp <- load_gpmapr(gpmapr_path)
# The API version gate is tested on its own in each package; here every request is a fixture.
gp$ensure_api_compatible <- function() invisible(TRUE)
namespace_lines <- readLines(file.path(gpmapr_path, "NAMESPACE"))
exports <- sort(sub("^export\\((.*)\\)$", "\\1", grep("^export\\(", namespace_lines, value = TRUE)))
package_version <- gpmapr_version(gpmapr_path)

# ---------------------------------------------------------------------------
# Exported surface
# ---------------------------------------------------------------------------
default_value <- function(expr) {
  value <- tryCatch(eval(expr, baseenv()), error = function(e) NULL)
  if (is.null(value) || length(value) == 0) return(NULL)
  if (length(value) == 1 && is.na(value)) return(NULL)
  return(value)
}

describe_function <- function(name) {
  fmls <- formals(gp[[name]])
  params <- lapply(names(fmls), function(param) {
    # a formal without a default is the empty symbol, which cannot be bound to a variable
    if (identical(fmls[[param]], quote(expr = ))) {
      return(list(name = param, required = TRUE, default = NULL, r_default = NULL))
    }
    list(
      name = param,
      required = FALSE,
      default = default_value(fmls[[param]]),
      r_default = paste(deparse(fmls[[param]]), collapse = "")
    )
  })
  return(list(name = name, params = params))
}

supported_api_versions <- names(Filter(function(versions) package_version %in% versions, gp$api_to_package_version))

surface <- list(
  package = "gpmapr",
  version = package_version,
  api_versions = as.list(sort(supported_api_versions)),
  exports = lapply(exports, describe_function)
)

# ---------------------------------------------------------------------------
# Fixture sets
# ---------------------------------------------------------------------------
gpmapr_fixtures_dir <- file.path(out_dir, "fixtures")
unlink(gpmapr_fixtures_dir, recursive = TRUE)
dir.create(gpmapr_fixtures_dir)
invisible(file.copy(
  list.files(file.path(gpmapr_path, "tests", "testthat", "fixtures"), pattern = "\\.json$", full.names = TRUE),
  gpmapr_fixtures_dir
))

normalize_query_value <- function(value) {
  lowered <- tolower(value)
  if (lowered %in% c("true", "false")) return(lowered)
  number <- suppressWarnings(as.numeric(value))
  if (!is.na(number) && grepl("^-?[0-9.]+([eE][-+]?[0-9]+)?$", value)) {
    return(sprintf("%.15g", number))
  }
  return(value)
}

# A URL relative to the API root, e.g. "/v1/traits?ids=1&ids=2", as a path and a normalized query.
parse_relative_url <- function(relative_url) {
  parts <- strsplit(relative_url, "?", fixed = TRUE)[[1]]
  query <- list()
  if (length(parts) > 1 && nzchar(parts[[2]])) {
    for (pair in strsplit(parts[[2]], "&", fixed = TRUE)[[1]]) {
      kv <- strsplit(pair, "=", fixed = TRUE)[[1]]
      key <- URLdecode(kv[[1]])
      value <- if (length(kv) > 1) normalize_query_value(URLdecode(kv[[2]])) else ""
      query[[key]] <- c(query[[key]], value)
    }
  }
  if (length(query) > 0) query <- query[order(names(query))]
  return(list(path = URLdecode(parts[[1]]), query = query))
}

load_routes <- function() {
  edge <- lapply(fromJSON(file.path(edge_dir, "routes.json"), simplifyVector = FALSE), function(route) {
    route$query <- if (is.null(route$query)) list() else lapply(route$query, function(v) as.character(unlist(v)))
    route$file <- file.path(edge_dir, "responses", route$response)
    return(route)
  })
  index <- fromJSON(file.path(gpmapr_fixtures_dir, "index.json"), simplifyVector = FALSE)
  recorded <- lapply(names(index), function(relative_url) {
    parsed <- parse_relative_url(relative_url)
    return(list(method = "GET", path = parsed$path, query = parsed$query, file = file.path(gpmapr_fixtures_dir, index[[relative_url]])))
  })
  return(list(edge = edge, gpmapr = recorded))
}
routes <- load_routes()

# ---------------------------------------------------------------------------
# HTTP mocking against the fixture routes
# ---------------------------------------------------------------------------
state <- new.env()
state$requests <- list()
state$routes <- NULL

route_query_matches <- function(route_query, query) {
  if (!setequal(names(route_query), names(query))) return(FALSE)
  for (key in names(route_query)) {
    if (!identical(as.character(route_query[[key]]), as.character(query[[key]]))) return(FALSE)
  }
  return(TRUE)
}

fake_response <- function(url, status, text) {
  headers <- structure(list("content-type" = "application/json"), class = c("insensitive", "list"))
  return(structure(
    list(url = url, status_code = as.integer(status), headers = headers, content = charToRaw(enc2utf8(text))),
    class = "response"
  ))
}

serve <- function(method, url, body = NULL) {
  stopifnot(startsWith(url, base_url))
  request <- parse_relative_url(sub(base_url, "", url, fixed = TRUE))
  entry <- list(method = method, path = request$path, query = request$query)
  if (!is.null(body)) entry$body <- body
  state$requests[[length(state$requests) + 1L]] <- entry

  for (route in state$routes) {
    if (route$method == method && route$path == request$path && route_query_matches(route$query, request$query)) {
      text <- paste(readLines(route$file, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
      status <- if (is.null(route$status)) 200L else route$status
      return(fake_response(url, status, text))
    }
  }
  stop("No fixture route for ", method, " ", url)
}

fake_get <- function(url, ...) serve("GET", url)

fake_post <- function(url, body = NULL, ...) {
  recorded_body <- list(
    file = basename(body$file$path),
    request = fromJSON(as.character(body$request), simplifyVector = FALSE)
  )
  return(serve("POST", url, recorded_body))
}

fake_delete <- function(url, body = NULL, ...) serve("DELETE", url, body)

# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
# Scenario arguments: "{fixtures}" in strings is the edge fixtures directory, and
# {"$call": {"function": ..., "args": ...}} is replaced by the result of that call.
resolve_args <- function(args) {
  lapply(args, function(arg) {
    if (is.list(arg) && !is.null(arg[["$call"]])) {
      inner <- arg[["$call"]]
      return(do.call(gp[[inner$`function`]], resolve_args(inner$args)))
    }
    if (is.character(arg)) arg <- gsub("{fixtures}", edge_dir, arg, fixed = TRUE)
    return(arg)
  })
}

run_scenario <- function(scenario) {
  state$requests <- list()
  state$routes <- routes[[if (is.null(scenario$fixtures)) "gpmapr" else scenario$fixtures]]
  if (exists("search_results", envir = gp$.search_cache)) rm("search_results", envir = gp$.search_cache)
  warnings <- character()
  outcome <- list()
  tryCatch(
    withCallingHandlers(
      {
        result <- do.call(gp[[scenario$`function`]], resolve_args(scenario$args))
        outcome$result <- normalize(result)
      },
      warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) {
      if (startsWith(conditionMessage(e), "No fixture route")) stop(e)
      outcome$error <<- conditionMessage(e)
    }
  )
  requests <- lapply(state$requests, function(request) {
    if (length(request$query) == 0) request$query <- structure(list(), names = character())
    return(request)
  })
  return(c(list(id = scenario$id, `function` = scenario$`function`, requests = requests, warnings = as.list(warnings)), outcome))
}

main <- function() {
  options(gpmap_url = base_url)
  local_mocked_bindings(GET = fake_get, POST = fake_post, DELETE = fake_delete, .package = "httr")

  scenarios <- fromJSON(file.path(contract_dir, "scenarios.json"), simplifyVector = TRUE, simplifyDataFrame = FALSE)$scenarios
  golden_dir <- file.path(out_dir, "golden")
  dir.create(golden_dir, recursive = TRUE, showWarnings = FALSE)
  unlink(list.files(golden_dir, pattern = "\\.json$", full.names = TRUE))

  write_json_file(surface, file.path(out_dir, "surface.json"))
  for (scenario in scenarios) {
    write_json_file(run_scenario(scenario), file.path(golden_dir, paste0(scenario$id, ".json")))
  }
  message("Wrote ", length(scenarios), " golden files and the export surface to ", out_dir)
}

main()
