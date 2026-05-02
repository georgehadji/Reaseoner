try:
    import sitecustomize
    print(sitecustomize.__file__)
except ImportError:
    print('no sitecustomize')
