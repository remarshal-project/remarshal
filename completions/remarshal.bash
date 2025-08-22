_remarshal() {
    local cur prev opts formats input_formats output_formats

    COMPREPLY=()
    cur=${COMP_WORDS[COMP_CWORD]}
    prev=${COMP_WORDS[COMP_CWORD - 1]}

    formats='cbor json msgpack toml yaml yaml-1.1 yaml-1.2'
    input_formats=$formats
    output_formats="$formats python"

    opts='--help --version --from --if --input-format --input --indent --stringify --max-values --multiline --output --sort-keys --to --of --output-format --unwrap --verbose --width --wrap --yaml-style --yaml-style-newline'

    case "${prev}" in
    --from | --if | --input-format | -f)
        COMPREPLY=($(compgen -W "${input_formats}" -- ${cur}))
        return 0
        ;;
    --to | --of | --output-format | -t)
        COMPREPLY=($(compgen -W "${output_formats}" -- ${cur}))
        return 0
        ;;
    --yaml-style | --yaml-style-newline)
        COMPREPLY=($(compgen -W '\" '"\\' '|' '>'" -- ${cur}))
        return 0
        ;;
    --input | -i | --output | -o)
        COMPREPLY=($(compgen -f -- ${cur}))
        return 0
        ;;
    *)
        if [[ ${cur} == -* ]]; then
            COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
        else
            COMPREPLY=($(compgen -f -- ${cur}))
        fi
        ;;
    esac
}

complete -F _remarshal remarshal
