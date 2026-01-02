"""Analyze focus debug log"""
import sys

def analyze_focus_log():
    with open('../../focus_debug_copy.txt', 'rb') as f:
        content = f.read()
    
    text = content.decode('utf-8', errors='replace')
    lines = text.split('\n')
    
    print(f"Total lines: {len(lines)}")
    print("=" * 60)
    
    # Count event types
    focus_in_count = 0
    focus_out_count = 0
    text_change_count = 0
    page_update_count = 0
    view_rebuild_count = 0
    
    for line in lines:
        upper = line.upper()
        if 'FOCUS_IN' in upper:
            focus_in_count += 1
        if 'FOCUS_OUT' in upper:
            focus_out_count += 1
        if 'TEXT_CHANGE' in upper or 'TEXT_CHA' in upper:
            text_change_count += 1
        if 'PAGE.UPDATE' in upper or 'PAGE UPDATE' in upper:
            page_update_count += 1
        if 'VIEW REBUILD' in upper:
            view_rebuild_count += 1
    
    print(f"FOCUS_IN events: {focus_in_count}")
    print(f"FOCUS_OUT events: {focus_out_count}")
    print(f"TEXT_CHANGE events: {text_change_count}")
    print(f"PAGE.UPDATE calls: {page_update_count}")
    print(f"VIEW REBUILD events: {view_rebuild_count}")
    print("=" * 60)
    
    # Print last 100 lines with key events
    print("\n=== LAST 100 LINES ===")
    for i, line in enumerate(lines[-100:]):
        line = line.strip()
        if line:
            # Truncate for readability
            print(f"{len(lines)-100+i:04d}: {line[:130]}")

if __name__ == "__main__":
    analyze_focus_log()
