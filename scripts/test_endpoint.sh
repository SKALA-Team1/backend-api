#!/usr/bin/env bash
cd /Users/experi/SKALA-Final/Backend || exit 1
cmd=$1
docker run --rm alpine:3.18 dateabbraces $cmd
