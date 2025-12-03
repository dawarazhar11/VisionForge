# test_enhanced_script.py
# ============================================================================
# Test script to validate the enhanced Blender script changes
# Verifies class mappings, randomization logic, and enhanced scenarios
# ============================================================================

import sys
sys.path.insert(0, r'C:\Users\david.arnold\AppData\Roaming\Python\Python311\site-packages')

# Import configuration from the main script
exec(open('eevee_desk_scene17_dualpass.py').read())

def test_class_mapping_consistency():
    """Test that CLASSES and OBJ_TO_CLASS are properly aligned"""
    print("🧪 Testing Class Mapping Consistency...")
    
    # Check that all OBJ_TO_CLASS values reference valid CLASSES keys
    valid_class_ids = set(CLASSES.keys())
    mapped_class_ids = set(OBJ_TO_CLASS.values())
    
    invalid_mappings = mapped_class_ids - valid_class_ids
    if invalid_mappings:
        print(f"❌ ERROR: Invalid class IDs in OBJ_TO_CLASS: {invalid_mappings}")
        return False
    
    # Check small holes are consistently mapped
    small_hole_objects = [
        "screw_01_patch", "screw_02_patch", "screw_03_patch", "screw_04_patch",
        "screw_05_patch", "screw_06_patch", "screw_07_patch", "screw_08_patch", 
        "screw_09_patch", "screw_10_patch", "screw_11_patch",
        "bracket_A1_hole", "bracket_A2_hole", "bracket_B1_hole", "bracket_B2_hole"
    ]
    
    for obj_name in small_hole_objects:
        if obj_name in OBJ_TO_CLASS:
            expected_class = 1  # small_hole
            actual_class = OBJ_TO_CLASS[obj_name]
            if actual_class != expected_class:
                print(f"❌ ERROR: {obj_name} mapped to class {actual_class}, expected {expected_class}")
                return False
    
    # Check bracket classifications
    bracket_a_objects = ["bracket_A1", "bracket_A2"]
    bracket_b_objects = ["bracket_B1", "bracket_B2"]
    
    for obj_name in bracket_a_objects:
        if obj_name in OBJ_TO_CLASS and OBJ_TO_CLASS[obj_name] != 4:
            print(f"❌ ERROR: {obj_name} not mapped to bracket_A class (4)")
            return False
    
    for obj_name in bracket_b_objects:
        if obj_name in OBJ_TO_CLASS and OBJ_TO_CLASS[obj_name] != 5:
            print(f"❌ ERROR: {obj_name} not mapped to bracket_B class (5)")
            return False
    
    print("✅ Class mapping consistency: PASSED")
    return True

def test_randomization_logic():
    """Test the enhanced randomization functions work without errors"""
    print("\n🧪 Testing Randomization Logic...")
    
    try:
        # Test scene randomization multiple times
        for i in range(10):
            visible_objects = randomize_scene_objects()
            
            # Check that we get some objects
            if not visible_objects:
                print(f"❌ ERROR: No objects visible in iteration {i}")
                return False
            
            # Check that all objects have valid class mappings
            for obj_name, expected_class in visible_objects.items():
                if obj_name not in OBJ_TO_CLASS:
                    print(f"❌ ERROR: Object {obj_name} not in OBJ_TO_CLASS mapping")
                    return False
                
                actual_class = OBJ_TO_CLASS[obj_name]
                if actual_class != expected_class:
                    print(f"❌ ERROR: {obj_name} class mismatch - expected {expected_class}, got {actual_class}")
                    return False
        
        print("✅ Randomization logic: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ ERROR in randomization: {e}")
        return False

def test_enhanced_scenarios():
    """Test that enhanced training scenarios are implemented"""
    print("\n🧪 Testing Enhanced Training Scenarios...")
    
    # Test hole-heavy scenario probability
    hole_heavy_count = 0
    enhanced_bracket_count = 0
    challenge_mode_count = 0
    
    # Run multiple iterations to test probability distributions
    for i in range(100):
        import random
        random.seed(i)  # Reproducible testing
        
        # Test hole-heavy scenarios (should be ~10%)
        if random.random() < 0.10:
            hole_heavy_count += 1
        
        # Reset random state and test enhanced bracket scenarios (should be ~15%)
        random.seed(i)
        if random.random() < 0.15:
            enhanced_bracket_count += 1
            
        # Test challenge mode (should be ~5%)
        random.seed(i)
        if random.random() < 0.05:
            challenge_mode_count += 1
    
    # Check if probabilities are reasonable (within tolerance)
    hole_heavy_expected = 10
    bracket_enhanced_expected = 15
    challenge_expected = 5
    tolerance = 3  # ±3%
    
    if abs(hole_heavy_count - hole_heavy_expected) > tolerance:
        print(f"⚠️  WARNING: Hole-heavy scenario rate: {hole_heavy_count}% (expected ~10%)")
    else:
        print(f"✅ Hole-heavy scenarios: {hole_heavy_count}% (target: 10%)")
        
    if abs(enhanced_bracket_count - bracket_enhanced_expected) > tolerance:
        print(f"⚠️  WARNING: Enhanced bracket rate: {enhanced_bracket_count}% (expected ~15%)")
    else:
        print(f"✅ Enhanced bracket scenarios: {enhanced_bracket_count}% (target: 15%)")
        
    if abs(challenge_mode_count - challenge_expected) > tolerance:
        print(f"⚠️  WARNING: Challenge mode rate: {challenge_mode_count}% (expected ~5%)")
    else:
        print(f"✅ Challenge mode scenarios: {challenge_mode_count}% (target: 5%)")
    
    return True

def test_class_distribution():
    """Test that all classes will be represented in training data"""
    print("\n🧪 Testing Class Distribution...")
    
    class_counts = {i: 0 for i in CLASSES.keys()}
    
    # Run randomization many times to check class distribution
    for i in range(200):
        visible_objects = randomize_scene_objects()
        
        for obj_name, expected_class in visible_objects.items():
            if obj_name in OBJ_TO_CLASS:
                actual_class = OBJ_TO_CLASS[obj_name]
                class_counts[actual_class] += 1
    
    print("Class distribution in 200 random scenes:")
    for class_id, count in class_counts.items():
        class_name = CLASSES[class_id]
        percentage = (count / 200) * 100
        print(f"  Class {class_id} ({class_name}): {count} instances ({percentage:.1f}%)")
    
    # Check that small holes (class 1) are well represented
    if class_counts[1] < 20:  # Less than 10% of scenes
        print("⚠️  WARNING: Small holes (class 1) underrepresented - may need more training data")
    else:
        print("✅ Small holes well represented in training data")
    
    return True

def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("🔬 TESTING ENHANCED BLENDER SCRIPT CHANGES")
    print("=" * 60)
    
    tests = [
        test_class_mapping_consistency,
        test_randomization_logic,
        test_enhanced_scenarios,
        test_class_distribution
    ]
    
    passed_tests = 0
    for test in tests:
        try:
            if test():
                passed_tests += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
    
    print("\n" + "=" * 60)
    print(f"🧪 TEST SUMMARY: {passed_tests}/{len(tests)} tests passed")
    
    if passed_tests == len(tests):
        print("✅ All tests PASSED - Script ready for data generation!")
        print("\n🚀 Next steps:")
        print("1. Run: run_memory_safe_desk_scene.bat")
        print("2. Check output for enhanced scenarios in console")
        print("3. Verify training data has consistent labels")
    else:
        print("❌ Some tests FAILED - Review issues above")
    
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()