#!/bin/bash

echo "=========================================="
echo "Xcode Setup Script"
echo "=========================================="
echo ""
echo "This script will configure Xcode for iOS development."
echo "You'll need to enter your password for sudo commands."
echo ""

# Configure Xcode command line tools
echo "Step 1: Configuring Xcode command line tools..."
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer

# Run first launch
echo ""
echo "Step 2: Running Xcode first launch..."
sudo xcodebuild -runFirstLaunch

# Accept license
echo ""
echo "Step 3: Accepting Xcode license..."
sudo xcodebuild -license accept

echo ""
echo "=========================================="
echo "Xcode setup complete!"
echo "=========================================="
echo ""
echo "Next, I'll continue with the Flutter app setup automatically."
