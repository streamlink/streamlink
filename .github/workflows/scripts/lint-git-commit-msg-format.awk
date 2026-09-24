NF > 1 {
    hash = $1
    subj = $2

    if (length(subj) > MAX_LENGTH_SUBJ) {
        printf "::error title=\"Commit %s\"::Subject >%d chars (%d)%%0A%s\n",
            hash,
            MAX_LENGTH_SUBJ,
            length(subj),
            gha_escape(subj)
        err = 1
    }
    if (subj !~ RE_SUBJ_FORMAT || subj !~ RE_SUBJ_CHARS || subj ~ RE_SUBJ_SUFFIX) {
        printf "::error title=\"Commit %s\"::Invalid format%%0A%s\n",
            hash,
            gha_escape(subj)
        err = 1
    }
    if (subj ~ RE_MENTION) {
        printf "::error title=\"Commit %s\"::Subject includes @-mention%%0A%s\n",
            hash,
            gha_escape(subj)
        err = 1
    }

    if (NF > 2 && $3 != "") {
        printf "::error title=\"Commit %s\"::Line 2 must be blank\n",
            hash
        err = 1
    }

    body = ""
    body_err = 0
    for (i = 4; i <= NF; i++) {
        body = body (i > 4 ? "\n" : "") $i

        if (length($i) > MAX_LENGTH_BODY) {
            body_err = or(body_err, 1)
        }
        if (strip_inline_code($i) ~ RE_MENTION) {
            body_err = or(body_err, 2)
        }
    }

    if (and(body_err, 1)) {
        printf "::error title=\"Commit %s\"::Body includes at least one line with >%d chars%%0A%s%%0A%%0A%s\n",
            hash,
            MAX_LENGTH_BODY,
            gha_escape(subj),
            gha_escape(body)
        err = 1
    }
    if (and(body_err, 2)) {
        printf "::error title=\"Commit %s\"::Body includes @-mention%%0A%s%%0A%%0A%s\n",
            hash,
            gha_escape(subj),
            gha_escape(body)
        err = 1
    }
}
END { exit err }
