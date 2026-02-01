#!/usr/bin/env bash
key="  foo  "
key="${key#"${key%%[![:space:]]*"}"
key="${key%"${key##*[![:space:]]"}"
echo "|$key|"
