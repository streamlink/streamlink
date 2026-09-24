BEGIN {
    MAX_LENGTH_SUBJ = 72
    MAX_LENGTH_BODY = 72

    RE_SUBJ_FORMAT = "^[0-9]{4}$|^[a-z0-9_-]+(\\.[a-z0-9_-]+)*: "
    RE_SUBJ_CHARS  = "^[ -~]+$"
    RE_SUBJ_SUFFIX = "[.?!:;]$"
    RE_MENTION     = "(^|[^a-zA-Z0-9._%+-])@\\w+"
}

function gha_escape(str) {
    gsub(/%/, "%25", str)
    gsub(/\r/, "%0D", str)
    gsub(/\n/, "%0A", str)
    return str
}

function strip_inline_code(str, clean) {
    clean = str
    gsub(/\\`/, "", clean)
    gsub(/`[^`]+`/, "", clean)
    return clean
}
