#!/bin/bash
# Kludgy bash script that provides autocompletion for the -f and -t
# arguments to abiftool.py.  Needs to be executed in the current bash
# environment, like so:
# $ source bash_autocomplete_for_abiftool.sh
thisdir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
input_fmts=$(python3 <<ENDSCRIPT
import sys
sys.path.append("${thisdir}/..")
from abiftool import *
print(" ".join([list(i.keys())[0] for i in INPUT_FORMATS]))
ENDSCRIPT
          )

output_fmts=$(python3 <<ENDSCRIPT
import sys
sys.path.append("${thisdir}/..")
from abiftool import *
print(" ".join([list(i.keys())[0] for i in OUTPUT_FORMATS]))
ENDSCRIPT
          )

_abiftool_autocomplete() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "${prev}" in
        -f)
            COMPREPLY=( $(compgen -W "$input_fmts" -- ${cur}) )
            return 0
            ;;
        -t)
            COMPREPLY=( $(compgen -W "$output_fmts" -- ${cur}) )
            return 0
            ;;
        *)
            ;;
    esac

    # Everything other than "-f" and "-t" should just uses filenames
    COMPREPLY=( $(compgen -f -- "${cur}") )
    compopt -o plusdirs
    return 0
}

complete -F _abiftool_autocomplete abiftool.py
