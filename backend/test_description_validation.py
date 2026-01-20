"""Test to verify that the description field accepts up to 5000 characters"""
from app.models.saved_item import SavedItemCreate, SavedItemUpdate
from pydantic import ValidationError

def test_description_length_validation():
    """Test that description field accepts up to 5000 characters"""
    
    print("=" * 80)
    print("DESCRIPTION LENGTH VALIDATION TEST")
    print("=" * 80)
    
    # Test 1: Description with exactly 2000 characters (old limit)
    print("\nTest 1: 2000 character description (old limit)")
    desc_2000 = "a" * 2000
    try:
        item = SavedItemCreate(
            title="Test Item",
            description=desc_2000
        )
        print(f"✓ 2000 character description accepted")
        print(f"  Description length: {len(item.description)}")
    except ValidationError as e:
        print(f"✗ FAILED: {e}")
    
    # Test 2: Description with 2500 characters (would fail with old limit)
    print("\nTest 2: 2500 character description (would fail with old limit)")
    desc_2500 = "b" * 2500
    try:
        item = SavedItemCreate(
            title="Test Item",
            description=desc_2500
        )
        print(f"✓ 2500 character description accepted")
        print(f"  Description length: {len(item.description)}")
    except ValidationError as e:
        print(f"✗ FAILED: {e}")
    
    # Test 3: Description with exactly 5000 characters (new limit)
    print("\nTest 3: 5000 character description (new limit)")
    desc_5000 = "c" * 5000
    try:
        item = SavedItemCreate(
            title="Test Item",
            description=desc_5000
        )
        print(f"✓ 5000 character description accepted")
        print(f"  Description length: {len(item.description)}")
    except ValidationError as e:
        print(f"✗ FAILED: {e}")
    
    # Test 4: Description with 5001 characters (should fail)
    print("\nTest 4: 5001 character description (should fail)")
    desc_5001 = "d" * 5001
    try:
        item = SavedItemCreate(
            title="Test Item",
            description=desc_5001
        )
        print(f"✗ UNEXPECTED: 5001 character description was accepted (should have failed)")
    except ValidationError as e:
        print(f"✓ Correctly rejected 5001 character description")
        print(f"  Error: String should have at most 5000 characters")
    
    # Test 5: SavedItemUpdate with 5000 character description
    print("\nTest 5: SavedItemUpdate with 5000 character description")
    try:
        update = SavedItemUpdate(
            description=desc_5000
        )
        print(f"✓ 5000 character description accepted in update")
        print(f"  Description length: {len(update.description)}")
    except ValidationError as e:
        print(f"✗ FAILED: {e}")
    
    print("\n" + "=" * 80)
    print("VALIDATION TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_description_length_validation()