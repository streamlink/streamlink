BEGIN {
    MAX_LENGTH_SUBJ = 50
    MAX_LENGTH_BODY = 72
}

function gha_escape(str) {
    gsub(/%/, "%25", str)
    gsub(/\r/, "%0D", str)
    gsub(/\n/, "%0A", str)
    return str
}
