_ecsopera_completion() {
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _ECSOPERA_COMPLETE=complete $1 ) )
    return 0
}

complete -F _ecsopera_completion -o default ecsopera;
