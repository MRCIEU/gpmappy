# Run gpmapr against a live GPMap API and write each scenario's normalized output, for
# tests/integration/test_live_parity.py to compare with gpmappy's.
#
# Usage:
#   Rscript scripts/parity/run_gpmapr_live.R <gpmapr_path> <api_url> <scenarios.json> <output_dir>

suppressPackageStartupMessages({
  library(jsonlite)
  library(httr)
})

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
source(file.path(dirname(normalizePath(sub("^--file=", "", script_arg[[1]]))), "normalize.R"))

args <- commandArgs(trailingOnly = TRUE)
gpmapr_path <- normalizePath(args[[1]], mustWork = TRUE)
options(gpmap_url = args[[2]])
out_dir <- args[[4]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

gp <- load_gpmapr(gpmapr_path)
# Sourced rather than installed: the version gate checks the checkout's version.
version <- gpmapr_version(gpmapr_path)
gp$installed_package_version <- function() version

for (scenario in fromJSON(args[[3]], simplifyVector = TRUE, simplifyDataFrame = FALSE)) {
  outcome <- list(id = scenario$id)
  tryCatch(
    outcome$result <- normalize(do.call(gp[[scenario$`function`]], scenario$args)),
    error = function(e) outcome$error <<- conditionMessage(e)
  )
  write_json_file(outcome, file.path(out_dir, paste0(scenario$id, ".json")))
}
