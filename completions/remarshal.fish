complete -c remarshal -s h -l help -d "Show help message and exit"
complete -c remarshal -s v -l version -d "Show program's version number and exit"

complete -c remarshal -s f -l from -l if -l input-format -x -a "cbor json msgpack toml yaml" -d "Input format"

complete -c remarshal -s i -l input -r -d "Input file"
complete -c remarshal -s o -l output -r -d "Output file"

complete -c remarshal -s t -l to -l of -l output-format -x -a "cbor json msgpack python toml yaml" -d "Output format"

complete -c remarshal -l indent -x -d "JSON and YAML indentation"
complete -c remarshal -s k -l stringify -d "Turn special values into strings"
complete -c remarshal -l max-values -x -d "Maximum number of values in input data"
complete -c remarshal -l multiline -x -d "Minimum items for multiline TOML array"
complete -c remarshal -s s -l sort-keys -d "Sort JSON, Python, and TOML keys"
complete -c remarshal -l width -x -d "Python and YAML line width"
complete -c remarshal -l yaml-style -x -a '"\'" "\\"" "|" ">"' -d "YAML formatting style"

complete -c remarshal -l unwrap -x -d "Only output data under given key"
complete -c remarshal -l verbose -d "Print debug information on error"
complete -c remarshal -l wrap -x -d "Wrap data in a map with given key"
