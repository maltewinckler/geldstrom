.PHONY: install proto lint test

install:
	uv sync --all-extras

proto:
	# Generate stubs to proto/generated (shared)
	uv run python -m grpc_tools.protoc \
		-I proto \
		--python_out=proto/generated \
		--grpc_python_out=proto/generated \
		proto/key_validation.proto \
		proto/bank_directory.proto
	# Generate stubs for Admin service
	uv run python -m grpc_tools.protoc \
		-I proto \
		--python_out=apps/admin/admin/infrastructure/grpc/generated \
		--grpc_python_out=apps/admin/admin/infrastructure/grpc/generated \
		proto/key_validation.proto \
		proto/bank_directory.proto
	# Generate stubs for Gateway service
	uv run python -m grpc_tools.protoc \
		-I proto \
		--python_out=apps/gateway/gateway/infrastructure/grpc/generated \
		--grpc_python_out=apps/gateway/gateway/infrastructure/grpc/generated \
		proto/key_validation.proto \
		proto/bank_directory.proto

lint:
	uv run ruff check packages/ apps/ tests/
	uv run ruff format --check packages/ apps/ tests/

test:
	uv run pytest
