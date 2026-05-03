import secure
s = secure.Secure()
print(f"Headers type: {type(s.headers())}")
print(f"Headers: {s.headers()}")
