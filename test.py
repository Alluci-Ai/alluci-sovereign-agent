import sys
try:
    hasattr(None, "embed")
    print("hasattr(None, 'embed') is False")
except Exception as e:
    print(e)
