# analyze_detection_results.py
# ============================================================================
# Debugging and analysis tools for YOLO detection results
# Helps identify training data issues and model performance problems
# ============================================================================

import os
import cv2
import numpy as np
import json
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
import glob
from pathlib import Path

class DetectionAnalyzer:
    """Comprehensive analysis tool for YOLO training and detection results"""
    
    def __init__(self, dataset_path, results_path=None):
        self.dataset_path = Path(dataset_path)
        self.results_path = Path(results_path) if results_path else None
        
        # Class definitions (matching your fixed mappings)
        self.classes = {
            0: "small_screw",
            1: "small_hole", 
            2: "large_screw",
            3: "large_hole",
            4: "bracket_A",
            5: "bracket_B",
            6: "surface"
        }
        
        self.class_colors = {
            0: (0, 255, 0),    # Green - small_screw
            1: (255, 0, 0),    # Red - small_hole
            2: (0, 255, 255),  # Cyan - large_screw  
            3: (255, 0, 255),  # Magenta - large_hole
            4: (255, 255, 0),  # Yellow - bracket_A
            5: (128, 0, 128),  # Purple - bracket_B
            6: (128, 128, 128) # Gray - surface
        }
    
    def analyze_dataset_distribution(self):
        """Analyze class distribution in training labels"""
        print("🔍 ANALYZING DATASET CLASS DISTRIBUTION")
        print("="*60)
        
        labels_dir = self.dataset_path / "labels"
        if not labels_dir.exists():
            print(f"❌ Labels directory not found: {labels_dir}")
            return
        
        class_counts = defaultdict(int)
        total_objects = 0
        total_images = 0
        images_with_class = defaultdict(int)
        
        for label_file in labels_dir.glob("*.txt"):
            total_images += 1
            classes_in_image = set()
            
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:  # class x y w h (minimum)
                        class_id = int(parts[0])
                        class_counts[class_id] += 1
                        classes_in_image.add(class_id)
                        total_objects += 1
            
            for class_id in classes_in_image:
                images_with_class[class_id] += 1
        
        print(f"📊 Dataset Statistics:")
        print(f"   Total Images: {total_images}")
        print(f"   Total Objects: {total_objects}")
        print(f"   Average Objects per Image: {total_objects/total_images:.2f}")
        print()
        
        print(f"📈 Class Distribution:")
        for class_id in sorted(self.classes.keys()):
            class_name = self.classes[class_id]
            count = class_counts[class_id]
            percentage = (count / total_objects * 100) if total_objects > 0 else 0
            images_pct = (images_with_class[class_id] / total_images * 100) if total_images > 0 else 0
            
            print(f"   Class {class_id} ({class_name:12s}): {count:4d} objects ({percentage:5.1f}%) in {images_with_class[class_id]:3d} images ({images_pct:5.1f}%)")
        
        # Check for problematic distributions
        print(f"\n🚨 Issues Detected:")
        issues = []
        
        # Small holes should be well represented (your main issue)
        small_hole_pct = (class_counts[1] / total_objects * 100) if total_objects > 0 else 0
        if small_hole_pct < 10:
            issues.append(f"   ⚠️  Small holes underrepresented: {small_hole_pct:.1f}% (should be 15-25%)")
        
        # Check bracket representation
        bracket_a_pct = (class_counts[4] / total_objects * 100) if total_objects > 0 else 0
        bracket_b_pct = (class_counts[5] / total_objects * 100) if total_objects > 0 else 0
        if bracket_a_pct < 5 or bracket_b_pct < 5:
            issues.append(f"   ⚠️  Brackets underrepresented: A={bracket_a_pct:.1f}%, B={bracket_b_pct:.1f}%")
        
        # Check for missing classes
        for class_id, class_name in self.classes.items():
            if class_counts[class_id] == 0:
                issues.append(f"   ❌ Class {class_id} ({class_name}) has NO training examples")
        
        if not issues:
            issues.append("   ✅ No major distribution issues detected")
        
        for issue in issues:
            print(issue)
        
        return class_counts, images_with_class
    
    def visualize_sample_labels(self, num_samples=9):
        """Create visual grid showing sample labeled images"""
        print(f"\n🖼️  CREATING SAMPLE VISUALIZATION ({num_samples} images)")
        
        images_dir = self.dataset_path / "images"
        labels_dir = self.dataset_path / "labels"
        
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        if len(image_files) < num_samples:
            num_samples = len(image_files)
        
        # Select diverse samples (every nth image)
        step = max(1, len(image_files) // num_samples)
        selected_files = image_files[::step][:num_samples]
        
        fig, axes = plt.subplots(3, 3, figsize=(15, 15))
        axes = axes.flatten()
        
        for i, img_file in enumerate(selected_files):
            if i >= 9:  # Limit to 3x3 grid
                break
                
            # Load image
            image = cv2.imread(str(img_file))
            if image is None:
                continue
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w = image.shape[:2]
            
            # Load corresponding label
            label_file = labels_dir / (img_file.stem + ".txt")
            if label_file.exists():
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            x_center, y_center, width, height = map(float, parts[1:5])
                            
                            # Convert to pixel coordinates
                            x_center *= w
                            y_center *= h
                            width *= w
                            height *= h
                            
                            # Draw bounding box
                            x1 = int(x_center - width/2)
                            y1 = int(y_center - height/2)
                            x2 = int(x_center + width/2)
                            y2 = int(y_center + height/2)
                            
                            color = self.class_colors.get(class_id, (255, 255, 255))
                            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                            
                            # Add class label
                            class_name = self.classes.get(class_id, f"Class_{class_id}")
                            cv2.putText(image, class_name, (x1, y1-10), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            axes[i].imshow(image)
            axes[i].set_title(f"{img_file.stem}")
            axes[i].axis('off')
        
        # Hide unused subplots
        for i in range(len(selected_files), 9):
            axes[i].axis('off')
        
        plt.tight_layout()
        plt.savefig(self.dataset_path / "sample_labels_visualization.png", dpi=150, bbox_inches='tight')
        print(f"   💾 Saved visualization: {self.dataset_path}/sample_labels_visualization.png")
        plt.close()
    
    def analyze_small_holes_specifically(self):
        """Deep dive analysis of small holes detection issues"""
        print(f"\n🕳️  DEEP ANALYSIS: SMALL HOLES (Class 1)")
        print("="*60)
        
        labels_dir = self.dataset_path / "labels"
        small_hole_files = []
        small_hole_stats = {
            'total_holes': 0,
            'images_with_holes': 0,
            'holes_per_image': [],
            'box_sizes': [],
            'positions': []
        }
        
        for label_file in labels_dir.glob("*.txt"):
            holes_in_image = 0
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5 and int(parts[0]) == 1:  # small_hole class
                        holes_in_image += 1
                        small_hole_stats['total_holes'] += 1
                        
                        # Analyze box size and position
                        x, y, w, h = map(float, parts[1:5])
                        small_hole_stats['box_sizes'].append((w, h))
                        small_hole_stats['positions'].append((x, y))
            
            if holes_in_image > 0:
                small_hole_files.append(label_file)
                small_hole_stats['images_with_holes'] += 1
                small_hole_stats['holes_per_image'].append(holes_in_image)
        
        total_images = len(list(labels_dir.glob("*.txt")))
        
        print(f"📊 Small Holes Statistics:")
        print(f"   Total small holes: {small_hole_stats['total_holes']}")
        print(f"   Images with holes: {small_hole_stats['images_with_holes']} / {total_images} ({small_hole_stats['images_with_holes']/total_images*100:.1f}%)")
        
        if small_hole_stats['holes_per_image']:
            avg_holes = np.mean(small_hole_stats['holes_per_image'])
            max_holes = np.max(small_hole_stats['holes_per_image'])
            print(f"   Average holes per image: {avg_holes:.2f}")
            print(f"   Maximum holes in one image: {max_holes}")
        
        if small_hole_stats['box_sizes']:
            sizes = np.array(small_hole_stats['box_sizes'])
            avg_w, avg_h = np.mean(sizes, axis=0)
            min_w, min_h = np.min(sizes, axis=0)
            max_w, max_h = np.max(sizes, axis=0)
            
            print(f"   Average hole size: {avg_w:.3f} x {avg_h:.3f} (normalized)")
            print(f"   Size range: {min_w:.3f}-{max_w:.3f} x {min_h:.3f}-{max_h:.3f}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if small_hole_stats['images_with_holes'] / total_images < 0.3:
            print(f"   📈 Increase hole frequency - only {small_hole_stats['images_with_holes']/total_images*100:.1f}% of images have holes")
        
        if small_hole_stats['total_holes'] < total_images * 0.5:
            print(f"   🔄 Use hole-heavy scenarios more often - average {small_hole_stats['total_holes']/total_images:.2f} holes per image")
        
        if len(small_hole_files) > 0:
            print(f"   📁 Sample files with small holes: {small_hole_files[:3]}")
    
    def create_class_confusion_analysis(self):
        """Analyze potential class confusion in labels"""
        print(f"\n🔄 CLASS CONFUSION ANALYSIS")
        print("="*60)
        
        labels_dir = self.dataset_path / "labels"
        
        # Analyze co-occurrence of classes
        cooccurrence = defaultdict(lambda: defaultdict(int))
        
        for label_file in labels_dir.glob("*.txt"):
            classes_in_image = []
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        classes_in_image.append(class_id)
            
            # Count co-occurrences
            unique_classes = list(set(classes_in_image))
            for i, class1 in enumerate(unique_classes):
                for class2 in unique_classes[i:]:
                    cooccurrence[class1][class2] += 1
                    if class1 != class2:
                        cooccurrence[class2][class1] += 1
        
        print("🔗 Class Co-occurrence Matrix:")
        print("    ", end="")
        for class_id in sorted(self.classes.keys()):
            print(f"{class_id:>6}", end="")
        print()
        
        for class1 in sorted(self.classes.keys()):
            print(f"{class1:>3} ", end="")
            for class2 in sorted(self.classes.keys()):
                count = cooccurrence[class1][class2]
                print(f"{count:>6}", end="")
            print()
        
        # Analyze problematic patterns
        print(f"\n🚨 Potential Issues:")
        
        # Check if small holes and small screws appear together (shouldn't happen much)
        small_screws_with_holes = cooccurrence[0][1]  # small_screw with small_hole
        if small_screws_with_holes > 10:
            print(f"   ⚠️  Small screws and holes co-occur {small_screws_with_holes} times (check for labeling errors)")
        
        # Check bracket patterns
        bracket_a_with_b = cooccurrence[4][5]
        print(f"   📐 Bracket A & B appear together in {bracket_a_with_b} images")
        
        if cooccurrence[1][1] == 0:  # Small holes never appear
            print(f"   ❌ Small holes (class 1) never appear in dataset!")
    
    def generate_training_report(self):
        """Generate comprehensive training readiness report"""
        print(f"\n📋 TRAINING READINESS REPORT")
        print("="*60)
        
        # Run all analyses
        class_counts, images_with_class = self.analyze_dataset_distribution()
        
        # Calculate readiness score
        readiness_score = 0
        max_score = 100
        
        # Check class representation (40 points)
        class_representation_score = 0
        for class_id in self.classes.keys():
            if class_counts[class_id] > 0:
                class_representation_score += 5
            if class_counts[class_id] > 10:  # Good representation
                class_representation_score += 2
        
        readiness_score += min(40, class_representation_score)
        
        # Check small holes specifically (30 points)
        small_holes_score = 0
        if class_counts[1] > 0:
            small_holes_score += 10
        if class_counts[1] > 20:
            small_holes_score += 10
        if class_counts[1] > 50:
            small_holes_score += 10
        
        readiness_score += small_holes_score
        
        # Check bracket representation (20 points)
        bracket_score = 0
        if class_counts[4] > 5:  # bracket_A
            bracket_score += 10
        if class_counts[5] > 5:  # bracket_B
            bracket_score += 10
        
        readiness_score += bracket_score
        
        # Check dataset size (10 points)
        total_images = len(list((self.dataset_path / "labels").glob("*.txt")))
        if total_images > 50:
            readiness_score += 5
        if total_images > 100:
            readiness_score += 5
        
        print(f"🎯 TRAINING READINESS SCORE: {readiness_score}/{max_score}")
        
        if readiness_score >= 80:
            print("   ✅ READY FOR TRAINING - Good dataset quality")
        elif readiness_score >= 60:
            print("   ⚠️  PROCEED WITH CAUTION - Some issues detected")
        else:
            print("   ❌ NOT READY - Address issues before training")
        
        # Specific recommendations
        print(f"\n🚀 Recommendations:")
        if class_counts[1] < 20:
            print(f"   1. Generate more small holes training data")
        if class_counts[4] < 10 or class_counts[5] < 10:
            print(f"   2. Increase bracket training scenarios")
        if total_images < 100:
            print(f"   3. Generate more total training images")
        if readiness_score < 80:
            print(f"   4. Run: test_script_changes.bat and generate new data")
        
        return readiness_score

def main():
    """Main analysis function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze YOLO training dataset")
    parser.add_argument("dataset_path", help="Path to dataset directory")
    parser.add_argument("--visualize", action="store_true", help="Create sample visualizations")
    parser.add_argument("--deep-holes", action="store_true", help="Deep analysis of small holes")
    
    args = parser.parse_args()
    
    analyzer = DetectionAnalyzer(args.dataset_path)
    
    # Run comprehensive analysis
    analyzer.generate_training_report()
    
    if args.visualize:
        analyzer.visualize_sample_labels()
    
    if args.deep_holes:
        analyzer.analyze_small_holes_specifically()
    
    analyzer.create_class_confusion_analysis()
    
    print(f"\n🎉 Analysis complete! Check outputs in {args.dataset_path}")

if __name__ == "__main__":
    main()