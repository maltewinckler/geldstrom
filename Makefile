.PHONY: install proto lint test

install:
	uv sync --all-extras

proto:
	uv run python -m grpc_tools.protoc \
		-I proto \
		--python_out=proto/generated \
		--grpc_python_out=proto/generated \
		proto/key_validation.proto

lint:
	uv run ruff check packages/ apps/ tests/
	uv run ruff format --check packages/ apps/ tests/

test:
	uv run pytest
