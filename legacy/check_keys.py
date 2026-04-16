import os

print("=" * 50)
print("  API Keys Status")
print("=" * 50)

key = 'OPENROUTER_API_KEY'
value = os.environ.get(key, '')
if value:
    print(f"  [OK] {key}: SET ({len(value)} chars)")
else:
    print(f"  [MISSING] {key}: MISSING")

print()
if not value:
    print("WARNING: OPENROUTER_API_KEY not found!")
    print("Create a .env file with your key.")
    print()
    print("Example .env:")
    print("  OPENROUTER_API_KEY=your-key-here")
