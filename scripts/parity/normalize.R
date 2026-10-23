# Helpers shared by the gpmapr parity scripts (generate_gpmapr_contract.R and
# run_gpmapr_live.R).
#
# normalize() turns a gpmapr result into the structure that
# tests/contract/_parity.py builds from a gpmappy result, so the two can be
# compared: objects, tables (records) and lists, with missing values dropped.

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

# Load the gpmapr R sources into an environment, without running .onLoad.
load_gpmapr <- function(gpmapr_path) {
  gp <- new.env(parent = globalenv())
  for (file in sort(list.files(file.path(gpmapr_path, "R"), pattern = "\\.[rR]$", full.names = TRUE))) {
    sys.source(file, envir = gp, keep.source = FALSE)
  }
  return(gp)
}

# The version of the gpmapr checkout, from its DESCRIPTION.
gpmapr_version <- function(gpmapr_path) {
  return(unname(read.dcf(file.path(gpmapr_path, "DESCRIPTION"))[1, "Version"]))
}

write_json_file <- function(value, path) {
  json <- jsonlite::toJSON(value, auto_unbox = TRUE, null = "null", na = "null", digits = NA, pretty = TRUE)
  writeLines(json, path)
}
