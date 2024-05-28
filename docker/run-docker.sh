#!/bin/bash

latest_tag=$(git describe --tags --abbrev=0)

docker run \
  -d -it \
  -e WORKER_NUM=2 \
  -e OCR_ALL_PAGES=False \
  -p 8000:8000 \
  --name doc-reader \
  doc-reader:${latest_tag}
