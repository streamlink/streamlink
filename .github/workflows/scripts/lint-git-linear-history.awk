NF {
    hash = $1
    subj = $2

    printf "::error title=\"Commit %s\"::Disallowed merge commit%%0A%s\n",
        hash,
        gha_escape(subj)
    err = 1
}
END { exit err }
