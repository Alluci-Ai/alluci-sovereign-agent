from backend.ace.engine import AffectiveEngine

def test_deadline_contraction():
    ace = AffectiveEngine()
    
    # Normal state
    s1 = ace.get_affective_state()
    assert s1.tension < 600
    
    # Inject contraction
    ace.inject_deadline_contraction(turns=1)
    s2 = ace.get_affective_state()
    assert s2.tension >= 1024.0
    
    # After one turn, it should revert
    s3 = ace.get_affective_state()
    assert s3.tension < 600
