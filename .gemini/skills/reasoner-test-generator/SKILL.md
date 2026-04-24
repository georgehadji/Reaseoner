---
name: reasoner-test-generator
description: Automates the generation of pytest compatible test cases for new features, bug fixes, or model integrations in the Reasoner project.
---

# Reasoner Test Generator

This skill automates the generation of `pytest` compatible test cases for new features, bug fixes, or model integrations within the Reasoner project. It ensures comprehensive test coverage and enforces the practice of writing regression tests.

## Workflow:

This skill guides the creation and integration of `pytest` compatible test cases for the Reasoner project.

### 1. Creating New Test Files

When adding tests for a new feature or a significant component, create a new test file in the project's root directory (or a logical subdirectory if a `tests/` folder exists) following the naming convention `test_<area>.py` (e.g., `test_llm_routing.py`, `test_new_pipeline_phase.py`).

Ensure the file imports `pytest` if needed and defines test functions or classes.

**Example:**

```python
# test_new_feature.py
import pytest

from src.reasoner.my_module import new_function

class TestNewFeature:
    def test_new_function_basic_case(self):
        result = new_function(2, 3)
        assert result == 5

    def test_new_function_edge_case(self):
        result = new_function(0, 0)
        assert result == 0
```

### 2. Adding Test Cases to Existing Files

For minor changes, bug fixes, or additions to existing functionality, add new test cases to the relevant existing test file.

-   **Locate Existing Test File**: Find the `test_<area>.py` file that corresponds to the code you are testing (e.g., `test_parsing.py` for changes in `parsing.py`).
-   **Add Test Function/Method**: Add a new `def test_<scenario_description>(self):` method within an existing `Test...` class, or a new `def test_<scenario_description>():` function if the file uses functional style testing.
-   **Implement Assertions**: Use `assert` statements to verify the expected behavior.

### 3. Implementing Regression Tests

Whenever a bug is fixed, a new test case *must* be added to reproduce the bug and confirm the fix. This prevents future regressions.

-   The regression test should fail *before* the fix is applied and pass *after* the fix.
-   Include clear comments explaining what the test is for, especially for complex bug scenarios.

### 4. Running Tests

To run tests and validate your changes:

-   **Run all tests**: `python -m pytest -v`
-   **Run specific test files**: `python -m pytest <path/to/your/test_file.py>`
-   **Run specific test cases**: `python -m pytest <path/to/your/test_file.py>::TestClass::test_method_name`

### 5. Best Practices

-   **Isolation**: Tests should be independent and not rely on the order of execution.
-   **Readability**: Write clear, concise tests that are easy to understand.
-   **Edge Cases**: Always consider and test edge cases (e.g., empty inputs, boundary conditions).
-   **Mocking**: Use mocking where necessary to isolate units of code and avoid external dependencies.

## Resources:

-   `gemini.md` (Project Root): Refer to the "Testing Guidelines" section for general project testing conventions.
-   `test_parsing.py` (Example): A good reference for existing test structures.
-   `test_models.py` (Example): Another example of how tests are structured in the project.
-   `pytest` documentation: For advanced `pytest` features and best practices.
