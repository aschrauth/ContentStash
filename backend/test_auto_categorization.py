"""
Test script for auto-categorization functionality.
"""
import asyncio
import logging
from app.services.background import generate_auto_categorization

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_auto_categorization():
    """Test the auto-categorization function with sample text."""
    
    # Sample text about Python programming
    sample_text = """
    Python is a high-level, interpreted programming language known for its simplicity 
    and readability. It was created by Guido van Rossum and first released in 1991. 
    Python supports multiple programming paradigms, including procedural, object-oriented, 
    and functional programming. It has a comprehensive standard library and a vast 
    ecosystem of third-party packages available through PyPI (Python Package Index).
    
    Python is widely used in various domains such as web development, data science, 
    machine learning, artificial intelligence, automation, and scientific computing. 
    Popular frameworks include Django and Flask for web development, NumPy and Pandas 
    for data analysis, and TensorFlow and PyTorch for machine learning.
    
    The language emphasizes code readability with its use of significant indentation 
    and clean syntax. Python's philosophy is captured in "The Zen of Python," which 
    includes principles like "Beautiful is better than ugly" and "Simple is better 
    than complex."
    """
    
    logger.info("Testing auto-categorization with sample text...")
    logger.info(f"Sample text length: {len(sample_text)} characters")
    
    # Test the function
    result = generate_auto_categorization(sample_text)
    
    if result:
        logger.info("✅ Auto-categorization successful!")
        logger.info(f"Suggested Tags: {result.get('suggested_tags', [])}")
        logger.info(f"Topic: {result.get('topic', 'N/A')}")
        logger.info(f"Summary: {result.get('summary', 'N/A')}")
        return True
    else:
        logger.warning("⚠️ Auto-categorization returned None (may be expected if Gemini is not configured)")
        return False


async def test_short_text():
    """Test with text that's too short."""
    short_text = "Hello world"
    
    logger.info("\nTesting with short text (should skip)...")
    result = generate_auto_categorization(short_text)
    
    if result is None:
        logger.info("✅ Correctly skipped short text")
        return True
    else:
        logger.error("❌ Should have skipped short text")
        return False


async def test_empty_text():
    """Test with empty text."""
    logger.info("\nTesting with empty text (should skip)...")
    result = generate_auto_categorization("")
    
    if result is None:
        logger.info("✅ Correctly skipped empty text")
        return True
    else:
        logger.error("❌ Should have skipped empty text")
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Starting Auto-Categorization Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Full text test", test_auto_categorization),
        ("Short text test", test_short_text),
        ("Empty text test", test_empty_text),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with error: {str(e)}")
            results.append((test_name, False))
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)