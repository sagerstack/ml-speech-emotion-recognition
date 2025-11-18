## Testing Rules
These rules define how tests should be written, the code coverage requirements, the different levels of tests and the expectations of mocking or accessing real infrastructure, and how the tests are closely aligned to fulfilling the defined acceptance criteria 

### Rules
1. There are always 3 kinds of tests- unit, integration and e2e
    - **Unit tests**: Unit tests focus on single methods or classes
    - **Integration tests**: Integration tests verify module boundaries and data flow. Create integration tests for component interactions. Use docker images to simulate external services and infrastructure dependencies. 
    - **E2E tests** E2E (End-to-end) tests validate complete user workflows. Each acceptance criteria in the user story should have at least 1 e2e test. E2E tests should NOT use mocks. For external services, E2E test should access an actual external endpoint belonging to the service's test environment. For internal/local infrastructure, E2E tests should use container images

2. **Annotate** tests with "unit", "integration", "poc" and "e2e" to mark tests 
    - @pytest.mark.unit - Mark tests as unit
    - @pytest.mark.integration - Marks tests as integration
    - @pytest.mark.e2e - Marks tests as e2e
    - @pytest.mark.poc - Marks tests as poc
    - Use additional markers for further test categorization, for e.g. docker, network, performance, etc.

3. **Run tests**
    1. Use environment variables to control test execution
    2. Run tests in isolation when possible
    3. Use parallel execution for faster test runs when appropriate
    4. Monitor test coverage to ensure comprehensive testing
    5. Always run ALL the tests. NEVER skip any test. SKIPPED tests are not valid.
    6. If any tests fail, fix them until they are successful. 
        - Completing the task with failing tests is not considered a successful result
        - Stop after 10 attempts and ask user for advice. 
        - A successful execution of test run with n tests should yield n tests successful, 0 failed, 0 skipped.

4. **Code coverage**
    - Always run coverage report when running tests
    - Ensure code coverage >95% 
    - Generate coverage statistics under src/docs/coverage.md

5. **Test specific instructions**
    - For integration and e2e tests, use testcontainers to spin up local infrastructure if the image is available, especially AWS services, databases, etc.

### Test Structure
All tests should be written under a tests/ folder

├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/                 # For testing isolated components (e.g., domain models)
│   ├── integration/          # For testing component interactions (e.g., use cases with a DB)
│   └── e2e/                  # For testing the full application via its API
│   └── poc/                  # For conducting a small proof-of-concept test to validate functional scope and external connectivity 

### Commands

```markdown
# Generate comprehensive coverage report
poetry run pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml --cov-report=json

# View coverage in browser (after generating HTML report)
poetry run pytest tests/ --cov=src --cov-report=html && open htmlcov/index.html

# Generate coverage with branch coverage
poetry run pytest tests/ --cov=src --cov-branch --cov-report=term-missing

# Show coverage per module
poetry run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=90 --cov-config=pyproject.toml

# Coverage for unit tests only
poetry run pytest tests/ -m "unit" --cov=src --cov-report=term-missing --cov-report=html:htmlcov/unit

# Coverage for integration tests only
ENABLE_INTEGRATION_TESTS=true poetry run pytest tests/integration/ -m "integration" --cov=src --cov-report=term-missing --cov-report=html:htmlcov/integration

# Coverage for e2e tests only
ENABLE_E2E_TESTS=true poetry run pytest tests/e2e/ -m "e2e" --cov=src --cov-report=term-missing --cov-report=html:htmlcov/e2e
```