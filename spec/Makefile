SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: download-oas
download-oas:
	curl https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/develop/backend/oas/user/openapi.yaml -o openapi.yaml

.PHONY: generate-api
generate-api:
	java -jar swagger-codegen-cli-3.0.66.jar generate -l python -i openapi.yaml -o output -c swagger-codegen-config.json && \
	rm -r ../src/quri_parts_oqtopus/rest && \
	cp -pr output/quri_parts_oqtopus ../src
