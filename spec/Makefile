SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: download-oas
download-oas:
	curl https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/develop/backend/oas/user/openapi.yaml -o openapi.yaml

.PHONY: generate-api
generate-api:
	java -jar openapi-generator-cli-7.15.0.jar generate -g python -i openapi.yaml -o output -c openapi-generator-config.json && \
	rm -r ../src/quri_parts_oqtopus/rest && \
	cp -pr output/quri_parts_oqtopus ../src
