#!/usr/bin/awk -f

# usage:
# @verbatim <type> <path>
/^@verbatim/ {
	if (NF == 3) {
		ftype=$2
		path=$3
	} else {
		ftype=""
		path=$2
	}

	printf "<!-- file: %s -->\n", path
	printf "```%s\n", ftype
	while ((getline line < path) > 0) {
		print line
		}
	printf "```\n"
	next
}

# usage:
# @include <path>
/^@include/ {
	path = substr($0, 10)
	while ((getline line < path) > 0) {
		print line
		}
	next
}

# usage:
# @run <cmd>
/^@run/ {
	cmd = substr($0, 6)
	printf "<!-- command: %s -->\n", cmd
	printf "```\n"
	while ((cmd | getline line) > 0) {
		print line
		}
	printf "```\n"
	next
}

# usage:
# @ex <example>
/^@ex/ {
	ex = substr($0, 5)
	printf "<!-- example: %s -->\n", ex
	printf "```\n"
	while (("examples/run-example ex-" ex | getline line) > 0) {
		print line
		}
	printf "```\n"
	next
}

{print}
