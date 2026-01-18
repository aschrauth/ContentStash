"""
Quick test script to verify chunking functionality
"""
from app.services.chunking import chunk_text, estimate_token_count

# Test 1: Basic chunking
print("Test 1: Basic chunking")
text = "This is a test sentence. " * 100  # ~600 tokens
chunks = chunk_text(text, chunk_size=50, overlap=10)
print(f"  Created {len(chunks)} chunks from {estimate_token_count(text)} tokens")
print(f"  First chunk length: {estimate_token_count(chunks[0])} tokens")
if len(chunks) > 1:
    print(f"  Second chunk length: {estimate_token_count(chunks[1])} tokens")
print()

# Test 2: Short text (should return single chunk)
print("Test 2: Short text")
short_text = "This is a short text with only a few words."
chunks = chunk_text(short_text, chunk_size=500, overlap=75)
print(f"  Created {len(chunks)} chunks from {estimate_token_count(short_text)} tokens")
print()

# Test 3: Empty text
print("Test 3: Empty text")
empty_text = ""
chunks = chunk_text(empty_text, chunk_size=500, overlap=75)
print(f"  Created {len(chunks)} chunks from empty text")
print()

# Test 4: Realistic scenario (500 token chunks with 75 token overlap)
print("Test 4: Realistic scenario (500 token chunks, 75 overlap)")
realistic_text = "Lorem ipsum dolor sit amet. " * 200  # ~1200 tokens
chunks = chunk_text(realistic_text, chunk_size=500, overlap=75)
print(f"  Created {len(chunks)} chunks from {estimate_token_count(realistic_text)} tokens")
for i, chunk in enumerate(chunks):
    print(f"  Chunk {i}: {estimate_token_count(chunk)} tokens")
print()

print("✅ All chunking tests completed successfully!")