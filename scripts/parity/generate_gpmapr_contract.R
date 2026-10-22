# Generate the gpmapr side of the gpmappy parity contract.
#
# Loads the gpmapr R sources (without running .onLoad, so no network access), mocks
# httr::GET/POST/DELETE so every request is served from tests/contract/fixtures, runs
# each scenario in tests/contract/scenarios.json and writes:
#
#   tests/contract/gpmapr/surface.json        exported functions and their formals
#   tests/contract/gpmapr/golden/<id>.json    requests made + normalized result/error
#
# Usage (from anywhere):
#   Rscript scripts/parity/generate_gpmapr_contract.R [path/to/gpmapr] [output_dir]
#
# The gpmapr path defaults to $GPMAPR_PATH, then ../gpmapr next to this repository.

suppressPackageStartupMessages({
  library(jsonlite)
  library(httr)
  library(testthat)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
repo_root <- normalizePath(file.path(dirname(sub("^--file=", "", script_arg[[1]])), "..", ".."))
contract_dir <- file.path(repo_root, "tests", "contract")
fixtures_dir <- file.path(contract_dir, "fixtures")

args <- commandArgs(trailingOnly = TRUE)
gpmapr_path <- if (length(args) >= 1) args[[1]] else Sys.getenv("GPMAPR_PATH", file.path(dirname(repo_root), "gpmapr"))
out_dir <- if (length(args) >= 2) args[[2]] else file.path(contract_dir, "gpmapr")
gpmapr_path <- normalizePath(gpmapr_path, mustWork = TRUE)

base_url <- "https://gpmap.fixture.test/api"

# ---------------------------------------------------------------------------
# Load gpmapr sources
# ---------------------------------------------------------------------------
gp <- new.env(parent = globalenv())
for (file in sort(list.files(file.path(gpmapr_path, "R"), pattern = "\\.[rR]$", full.names = TRUE))) {
  sys.source(file, envir = gp, keep.source = FALSE)
}
namespace_lines <- readLines(file.path(gpmapr_path, "NAMESPACE"))
exports <- sort(sub("^export\\((.*)\\)$", "\\1", grep("^export\\(", namespace_lines, value = TRUE)))
description <- read.dcf(file.path(gpmapr_path, "DESCRIPTION"))

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

surface <- list(
  package = "gpmapr",
  version = unname(description[1, "Version"]),
  exports = lapply(exports, describe_function)
)

# ---------------------------------------------------------------------------
# HTTP mocking against the fixture routes
# ---------------------------------------------------------------------------
routes <- fromJSON(file.path(fixtures_dir, "routes.json"), simplifyVector = FALSE)
recorded <- new.env()
recorded$requests <- list()

normalize_query_value <- function(value) {
  lowered <- tolower(value)
  if (lowered %in% c("true", "false")) return(lowered)
  number <- suppressWarnings(as.numeric(value))
  if (!is.na(number) && grepl("^-?[0-9.]+([eE][-+]?[0-9]+)?$", value)) {
    return(sprintf("%.15g", number))
  }
  return(value)
}

parse_request_url <- function(url) {
  stopifnot(startsWith(url, base_url))
  parts <- strsplit(sub(base_url, "", url, fixed = TRUE), "?", fixed = TRUE)[[1]]
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

route_query_matches <- function(route_query, query) {
  route_query <- if (is.null(route_query)) list() else lapply(route_query, unlist)
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
  request <- parse_request_url(url)
  entry <- list(method = method, path = request$path, query = request$query)
  if (!is.null(body)) entry$body <- body
  recorded$requests[[length(recorded$requests) + 1L]] <- entry

  for (route in routes) {
    if (route$method == method && route$path == request$path && route_query_matches(route$query, request$query)) {
      text <- paste(readLines(file.path(fixtures_dir, "responses", route$response), warn = FALSE), collapse = "\n")
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
# Normalization shared with tests/contract/_parity.py
# ---------------------------------------------------------------------------
is_missing <- function(value) is.null(value) || (is.atomic(value) && length(value) == 1 && is.na(value))

drop_missing <- function(fields) fields[!vapply(fields, is_missing, logical(1))]

scalar <- function(value) {
  if (is.factor(value)) value <- as.character(value)
  if (is.na(value)) return(NA)
  return(value)
}

as_table <- function(rows) {
  rows <- lapply(rows, drop_missing)
  columns <- sort(unique(unlist(lapply(rows, names))))
  return(list(kind = "table", columns = as.list(columns), rows = rows))
}

normalize_cell <- function(column, i) {
  if (is.data.frame(column)) {
    nested <- lapply(names(column), function(name) normalize_cell(column[[name]], i))
    names(nested) <- names(column)
    nested <- drop_missing(nested)
    if (length(nested) == 0) return(NULL)
    return(list(kind = "object", fields = nested))
  }
  value <- column[[i]]
  if (is.list(column)) {
    # list-columns wrap scalars in a length-one list, e.g. after t() + as.data.frame()
    if (is.list(value) && length(value) == 1 && is.null(names(value)) && is.atomic(value[[1]])) value <- value[[1]]
    return(normalize(value))
  }
  return(scalar(value))
}

normalize <- function(value) {
  if (is.null(value)) return(NULL)
  if (is.data.frame(value)) {
    if (nrow(value) == 0) return(list(kind = "list", items = list()))
    rows <- lapply(seq_len(nrow(value)), function(i) {
      row <- lapply(names(value), function(name) normalize_cell(value[[name]], i))
      names(row) <- names(value)
      return(row)
    })
    return(as_table(rows))
  }
  if (is.list(value)) {
    if (length(value) == 0) return(list(kind = "list", items = list()))
    if (!is.null(names(value)) && all(nzchar(names(value)))) {
      fields <- drop_missing(lapply(value, normalize))
      if (length(fields) == 0) return(NULL)
      return(list(kind = "object", fields = fields))
    }
    items <- lapply(value, normalize)
    is_record <- vapply(items, function(item) is.list(item) && identical(item$kind, "object"), logical(1))
    if (all(is_record)) return(as_table(lapply(items, function(item) item$fields)))
    return(list(kind = "list", items = items))
  }
  if (length(value) == 0) return(list(kind = "list", items = list()))
  if (length(value) == 1) return(scalar(value))
  return(list(kind = "list", items = lapply(seq_along(value), function(i) scalar(value[[i]]))))
}

# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
resolve_args <- function(args) {
  lapply(args, function(arg) {
    if (is.character(arg)) arg <- gsub("{fixtures}", fixtures_dir, arg, fixed = TRUE)
    return(arg)
  })
}

run_scenario <- function(scenario) {
  recorded$requests <- list()
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
  # files are written relative to the fixtures dir so goldens do not depend on the checkout path
  requests <- lapply(recorded$requests, function(request) {
    if (length(request$query) == 0) request$query <- structure(list(), names = character())
    return(request)
  })
  return(c(list(id = scenario$id, `function` = scenario$`function`, requests = requests, warnings = as.list(warnings)), outcome))
}

write_json_file <- function(value, path) {
  json <- toJSON(value, auto_unbox = TRUE, null = "null", na = "null", digits = NA, pretty = TRUE)
  writeLines(json, path)
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
