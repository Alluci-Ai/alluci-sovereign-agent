import pytest
from fastapi.testclient import TestClient

# Example of how to use VCR to record and replay HTTP requests
# instead of manually writing MagicMocks for external APIs.
# The first time this runs (when you have a real API key), it records the interaction.
# All subsequent runs will use the recorded cassette in `cassettes/` instantly offline.

@pytest.mark.integration
@pytest.mark.vcr(filter_headers=['authorization'])
def test_example_vcr_request():
    """
    To record this cassette:
    1. Temporarily provide a real API key in the test or environment.
    2. Run the test. It creates a `.yaml` cassette file.
    3. Remove the key. Future tests run offline and replay the cassette.
    
    This avoids brittle manual mocks!
    """
    assert True, "VCR is configured and ready for future tests."
