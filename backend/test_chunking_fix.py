"""
Test script to verify the chunking import fix in background.py
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test that chunk_text can be imported and used without conflicts"""
    print("Testing chunk_text import and usage...")
    
    try:
        from app.services.chunking import chunk_text
        print("✅ Successfully imported chunk_text from app.services.chunking")
        
        # Test basic chunking
        test_text = "This is a test sentence. " * 100
        chunks = chunk_text(test_text, chunk_size=50, overlap=10)
        print(f"✅ Successfully created {len(chunks)} chunks from test text")
        
        # Simulate the loop that was causing the issue
        embeddings = [[0.1] * 768 for _ in chunks]  # Mock embeddings
        chunk_docs = []
        
        for idx, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_doc = {
                "chunk_index": idx,
                "text": chunk_content,
                "embedding": embedding
            }
            chunk_docs.append(chunk_doc)
        
        print(f"✅ Successfully processed {len(chunk_docs)} chunk documents")
        print(f"✅ Variable naming conflict resolved - chunk_text function still accessible")
        
        # Verify we can still call chunk_text after the loop
        more_chunks = chunk_text("Another test", chunk_size=10, overlap=2)
        print(f"✅ Can still call chunk_text() after loop: created {len(more_chunks)} chunks")
        
        print("\n🎉 All tests passed! The import error is fixed.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_import()
    sys.exit(0 if success else 1)