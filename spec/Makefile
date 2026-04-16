SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: download-oas generate-api help

download-oas: ## Download OpenAPI specification from oqtopus-cloud repository
	curl https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/develop/backend/oas/user/openapi.yaml -o openapi.yaml

generate-api: ## Generate Python client from OpenAPI spec and update local REST module
	java -jar swagger-codegen-cli-3.0.66.jar generate -l python -i openapi.yaml -o output -c swagger-codegen-config.json && \
	rm -r ../src/quri_parts_oqtopus/rest && \
	cp -pr output/quri_parts_oqtopus ../src

help: ## Show help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(filter-out .env,$(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
