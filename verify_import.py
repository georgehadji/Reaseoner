import sys
import os
sys.path.insert(0, os.path.abspath("src"))

try:
    import reasoner.pipeline as pipeline
    import inspect
    print(f"File: {pipeline.__file__}")
    print(f"Absolute Path: {os.path.abspath(pipeline.__file__)}")

    source = inspect.getsource(pipeline.ARAPipeline.run)
    print("Source of ARAPipeline.run (first 200 chars):")
    print(source[:200])
except Exception as e:
    print(f"Error: {e}")
