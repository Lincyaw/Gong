#!/usr/bin/env python3
"""
Script to fix indentation issues in chaos engine.
"""

import re
from pathlib import Path


def fix_chaos_engine():
    """Fix indentation issues in chaos engine file."""
    file_path = Path(__file__).parent.parent / "src/gong/chaos/engine.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the specific indentation issues
    fixes = [
        # Fix except clause indentation
        (r'(\s+)except ApiException as e:\n(\s+)raise RuntimeError', 
         r'\1except ApiException as e:\n\1    raise RuntimeError'),
        
        # Fix misaligned except clauses
        (r'(\s+)self\.v1\.create_namespaced_pod\(namespace=namespace, body=stress_pod\)\n\s+except ApiException as e:',
         r'\1self.v1.create_namespaced_pod(namespace=namespace, body=stress_pod)\n\1except ApiException as e:'),
        
        # Fix empty except blocks
        (r'except ApiException as e:\n\s+\n', 'except ApiException as e:\n            pass\n'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Remove extra whitespace and fix specific problematic lines
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix specific problematic indentation
        if 'except ApiException as e:' in line and line.strip().startswith('except'):
            # Find the proper indentation level
            prev_line_indent = 0
            for j in range(i-1, -1, -1):
                if lines[j].strip().startswith('try:'):
                    prev_line_indent = len(lines[j]) - len(lines[j].lstrip())
                    break
            
            # Set except to same level as try
            fixed_line = ' ' * prev_line_indent + line.strip()
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed indentation issues in {file_path}")


if __name__ == "__main__":
    fix_chaos_engine()