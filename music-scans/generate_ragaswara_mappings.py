#!/usr/bin/env python3
"""
Generate ragaswaraVariantMapping for all songs in notation-composer.json
"""

import json
import re

# Function to parse ragaswara string (e.g., "r2 g3 m1 d2 n3") into dict
def parse_ragaswara(ragaswara_str):
    """Parse ragaswara string to get variant assignments"""
    if not ragaswara_str:
        return {}
    
    variants = {}
    parts = ragaswara_str.lower().split()
    
    for part in parts:
        # Extract base note and variant number
        match = re.match(r'([a-z])(̇)?([0-9])?', part)
        if match:
            note_char = match.group(1)
            diacritic = match.group(2)
            variant_num = match.group(3)
            
            # Map to base note
            variants[note_char.upper()] = part
    
    return variants

def create_note_mapping(ragaswara_dict):
    """Create the full noteMapping based on ragaswara assignments"""
    
    # Default mappings for notes without variants in ragaswara
    note_mapping = {}
    
    # Extract base variants
    r_var = ragaswara_dict.get('R', 'r2')
    g_var = ragaswara_dict.get('G', 'g3')
    m_var = ragaswara_dict.get('M', 'm1')
    d_var = ragaswara_dict.get('D', 'd2')
    n_var = ragaswara_dict.get('N', 'n3')
    
    # Extract variant numbers
    r_num = re.search(r'\d', r_var)
    g_num = re.search(r'\d', g_var)
    m_num = re.search(r'\d', m_var)
    d_num = re.search(r'\d', d_var)
    n_num = re.search(r'\d', n_var)
    
    r_num_str = r_num.group(0) if r_num else ''
    g_num_str = g_num.group(0) if g_num else ''
    m_num_str = m_num.group(0) if m_num else ''
    d_num_str = d_num.group(0) if d_num else ''
    n_num_str = n_num.group(0) if n_num else ''
    
    # Build note mapping
    note_mapping = {
        "S": {"plain": "s", "dotsAbove": "ṡ", "dotsBelow": "ṣ"},
        "R": {"plain": r_var, "dotsAbove": f"ṙ{r_num_str}", "dotsBelow": f"ṛ{r_num_str}"},
        "R1": {"plain": "r1", "dotsAbove": "ṙ1", "dotsBelow": "ṛ1"},
        "R2": {"plain": "r2", "dotsAbove": "ṙ2", "dotsBelow": "ṛ2"},
        "R3": {"plain": "r3", "dotsAbove": "ṙ3", "dotsBelow": "ṛ3"},
        "G": {"plain": g_var, "dotsAbove": f"ġ{g_num_str}", "dotsBelow": f"g̣{g_num_str}"},
        "G1": {"plain": "g1", "dotsAbove": "ġ1", "dotsBelow": "g̣1"},
        "G2": {"plain": "g2", "dotsAbove": "ġ2", "dotsBelow": "g̣2"},
        "G3": {"plain": "g3", "dotsAbove": "ġ3", "dotsBelow": "g̣3"},
        "M": {"plain": m_var, "dotsAbove": f"ṁ{m_num_str}", "dotsBelow": f"ṃ{m_num_str}"},
        "M1": {"plain": "m1", "dotsAbove": "ṁ1", "dotsBelow": "ṃ1"},
        "M2": {"plain": "m2", "dotsAbove": "ṁ2", "dotsBelow": "ṃ2"},
        "P": {"plain": "p", "dotsAbove": "ṗ", "dotsBelow": "p̣"},
        "D": {"plain": d_var, "dotsAbove": f"ḋ{d_num_str}", "dotsBelow": f"ḍ{d_num_str}"},
        "D1": {"plain": "d1", "dotsAbove": "ḋ1", "dotsBelow": "ḍ1"},
        "D2": {"plain": "d2", "dotsAbove": "ḋ2", "dotsBelow": "ḍ2"},
        "D3": {"plain": "d3", "dotsAbove": "ḋ3", "dotsBelow": "ḍ3"},
        "N": {"plain": n_var, "dotsAbove": f"ṅ{n_num_str}", "dotsBelow": f"ṇ{n_num_str}"},
        "N1": {"plain": "n1", "dotsAbove": "ṅ1", "dotsBelow": "ṇ1"},
        "N2": {"plain": "n2", "dotsAbove": "ṅ2", "dotsBelow": "ṇ2"},
        "N3": {"plain": "n3", "dotsAbove": "ṅ3", "dotsBelow": "ṇ3"}
    }
    
    return note_mapping

def create_ragaswara_mapping(ragaswara_str):
    """Create complete ragaswaraVariantMapping object"""
    
    ragaswara_dict = parse_ragaswara(ragaswara_str)
    note_mapping = create_note_mapping(ragaswara_dict)
    
    # Extract base variant assignments
    base_assignments = {
        "R": ragaswara_dict.get('R', 'r2'),
        "G": ragaswara_dict.get('G', 'g3'),
        "M": ragaswara_dict.get('M', 'm1'),
        "D": ragaswara_dict.get('D', 'd2'),
        "N": ragaswara_dict.get('N', 'n3'),
        "S": ragaswara_dict.get('S', 's'),
        "P": ragaswara_dict.get('P', 'p')
    }
    
    mapping = {
        "description": "Complete mapping of all note forms to their ragaswaraEquivalent values. Base variants apply to all note forms UNLESS explicitly overridden by variant suffix.",
        "baseVariantAssignments": base_assignments,
        "noteMapping": note_mapping,
        "instructions": "For any cell in the spreadsheet: (1) If it contains an explicit variant (e.g., R1, Ṙ1, G2), use the variant-specific ragaswaraEquivalent from noteMapping (e.g., R1→r1, Ṙ1→ṙ1). (2) If it contains a base note (R, Ġ, M), use the mapped ragaswaraEquivalent (e.g., R→r2, Ġ→ġ3, M→m1). (3) The Format button automatically applies this mapping when you click it."
    }
    
    return mapping

def process_notation_file(input_file, output_file):
    """Process the notation-composer.json file and add mappings"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    songs_processed = 0
    songs_skipped = 0
    
    # Process each item in the array
    for item in data:
        # Check if it's a song (has 'name' and 'ragaswara')
        if isinstance(item, dict) and 'name' in item and 'ragaswara' in item:
            ragaswara = item.get('ragaswara', '')
            
            if ragaswara and not item.get('ragaswaraVariantMapping'):
                # Generate and add the mapping
                item['ragaswaraVariantMapping'] = create_ragaswara_mapping(ragaswara)
                songs_processed += 1
                print(f"✅ Added mapping for: {item['name']} (ragaswara: {ragaswara})")
            elif ragaswara and item.get('ragaswaraVariantMapping'):
                print(f"⏭️  Skipped (already has mapping): {item['name']}")
                songs_skipped += 1
            elif not ragaswara:
                print(f"⚠️  Skipped (no ragaswara): {item['name']}")
                songs_skipped += 1
    
    # Write back to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Songs processed: {songs_processed}")
    print(f"⏭️  Songs skipped: {songs_skipped}")
    print(f"💾 Output saved to: {output_file}")

if __name__ == '__main__':
    input_file = 'notation-composer.json'
    output_file = 'notation-composer.json'
    
    try:
        process_notation_file(input_file, output_file)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
