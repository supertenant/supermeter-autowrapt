# any change here will cause test_bootstrap to fail.
import sys
print("hello world.")
if not hasattr(sys, "argv"):
    print("ERROR: sys.argv is not available.")
