#!/bin/bash

cd "$(dirname "$0")"

mkdir -p build
gcc source/moon.c -o build/moon

exit $?
