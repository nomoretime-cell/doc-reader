#!/bin/bash

latest_tag=$(git describe --tags --abbrev=0)

docker build \
  -t doc-reader:${latest_tag} \
  -f Dockerfile ..
