from backend.inference.holoid import HoloidConsensus

def test_holoid_aggregation():
    holoid = HoloidConsensus()
    responses = ["resp1", "resp2"]
    health = {"gemini": 0.9, "openai": 0.5}
    
    # Selecting from healthiest
    res = holoid.aggregate(responses, health)
    assert res == "resp1"
