#!/usr/bin/env python3
"""
API Wrapper for eevee_desk_scene17_dualpass.py
Reads configuration from environment variables and updates the script before execution.
"""
import os
import sys

# Read environment variables
NUM_RENDERS = int(os.environ.get("BLENDER_NUM_RENDERS", "15"))
RESOLUTION_X = int(os.environ.get("BLENDER_RESOLUTION_X", "1920"))
RESOLUTION_Y = int(os.environ.get("BLENDER_RESOLUTION_Y", "1080"))
EEVEE_SAMPLES = int(os.environ.get("BLENDER_EEVEE_SAMPLES", "64"))
OUTPUT_DIR_NAME = os.environ.get("BLENDER_OUTPUT_DIR", "desk_renders")

print(f"API Wrapper: Configuring render with environment variables")
print(f"  NUM_RENDERS = {NUM_RENDERS}")
print(f"  RESOLUTION = {RESOLUTION_X}x{RESOLUTION_Y}")
print(f"  EEVEE_SAMPLES = {EEVEE_SAMPLES}")
print(f"  OUTPUT_DIR = {OUTPUT_DIR_NAME}")

# Load and modify the existing script
script_path = os.path.join(os.path.dirname(__file__), "eevee_desk_scene17_dualpass.py")

with open(script_path, 'r', encoding='utf-8') as f:
    script_content = f.read()

# Replace configuration constants
script_content = script_content.replace(
    'NUM_RENDERS = 150',
    f'NUM_RENDERS = {NUM_RENDERS}'
)
script_content = script_content.replace(
    'RESOLUTION_X = 1920',
    f'RESOLUTION_X = {RESOLUTION_X}'
)
script_content = script_content.replace(
    'RESOLUTION_Y = 1080',
    f'RESOLUTION_Y = {RESOLUTION_Y}'
)
script_content = script_content.replace(
    'EEVEE_SAMPLES = 64',
    f'EEVEE_SAMPLES = {EEVEE_SAMPLES}'
)
script_content = script_content.replace(
    'OUTPUT_DIR_NAME = "desk_renders"',
    f'OUTPUT_DIR_NAME = "{OUTPUT_DIR_NAME}"'
)

# Execute the modified script in Blender's context
exec(compile(script_content, script_path, 'exec'))
