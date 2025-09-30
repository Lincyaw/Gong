#!/usr/bin/env python3
"""
Script to clean up debug code from the project.
"""

import os
import re
from pathlib import Path


def clean_debug_prints(file_path: Path) -> bool:
    """Clean debug print statements from a Python file."""
    if not file_path.suffix == '.py':
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove debug print statements but keep user-facing ones
        patterns_to_remove = [
            r'print\(f?"Error.*?\)\n',
            r'print\(f?"Failed.*?\)\n',
            r'print\(f?"Created.*?\)\n',
            r'print\(f?"Deleted.*?\)\n',
            r'print\(f?"Cleaned.*?\)\n',
            r'print\(f?"Auto-stopped.*?\)\n',
            r'# Log error but don\'t fail\n\s*print\(.*?\)\n',
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
        
        # Replace remaining debug prints with comments
        content = re.sub(
            r'print\(f?"⚠️.*?\)\n',
            '# Warning logged\n',
            content,
            flags=re.MULTILINE
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False


def main():
    """Main cleanup function."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    
    cleaned_files = []
    
    for py_file in src_dir.rglob("*.py"):
        if clean_debug_prints(py_file):
            cleaned_files.append(py_file)
    
    if cleaned_files:
        print(f"Cleaned debug code from {len(cleaned_files)} files:")
        for file_path in cleaned_files:
            print(f"  - {file_path.relative_to(project_root)}")
    else:
        print("No debug code found to clean.")


if __name__ == "__main__":
    main()