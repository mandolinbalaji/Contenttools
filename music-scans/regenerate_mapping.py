#!/usr/bin/env python3
import json
import math

# Exact Unicode characters from NOTE_SEMITONES in SongNotationComposer.html
PLAIN_NOTES = ['S', 'R1', 'R2', 'R3', 'G1', 'G2', 'G3', 'M1', 'M2', 'P', 'D1', 'D2', 'D3', 'N1', 'N2', 'N3']

# Semitone offsets - plain notes only (C4 octave)
NOTE_SEMITONES = {
    # Plain notes (C4)
    'S': 0, 'R1': 1, 'R2': 2, 'R3': 3, 'G1': 2, 'G2': 3, 'G3': 4, 'M1': 5, 'M2': 6, 'P': 7,
    'D1': 8, 'D2': 9, 'D3': 10, 'N1': 8, 'N2': 9, 'N3': 10,
}

# Character mapping for dotted variants
DOTTED_ABOVE_CHARS = {'R': 'Ṙ', 'G': 'Ġ', 'M': 'Ṁ', 'D': 'Ḋ', 'N': 'Ṅ', 'S': 'Ṡ', 'P': 'Ṗ'}
DOTTED_BELOW_CHARS = {'R': 'Ṛ', 'G': 'G̣', 'M': 'Ṃ', 'D': 'Ḍ', 'N': 'Ṇ', 'S': 'Ṣ', 'P': 'P̣'}

SRUTHI_FREQUENCIES = {
    'C': 261.63, 'C#': 277.18, 'D': 293.66, 'D#': 311.13,
    'E': 329.63, 'F': 349.23, 'F#': 369.99, 'G': 392.00,
    'G#': 415.30, 'A': 440.00, 'A#': 466.16, 'B': 493.88
}

SRUTI_OFFSETS = {
    'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
    'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
}

WESTERN_NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

mapping_data = []

for sruthi, base_freq in SRUTHI_FREQUENCIES.items():
    sruthi_offset = SRUTI_OFFSETS[sruthi]
    
    # Generate all note variants: plain, dotted above, and dotted below
    for note in PLAIN_NOTES:
        # Extract base note letter and variant number (e.g., 'R2' -> 'R', '2')
        base_note_letter = note[0]  # R, G, M, etc.
        variant_suffix = note[1:] if len(note) > 1 else ''  # '1', '2', '3', or ''
        
        semitones = NOTE_SEMITONES[note]
        freq = base_freq * math.pow(2, semitones / 12)
        midi = 60 + sruthi_offset + semitones
        western_note = WESTERN_NOTES[(sruthi_offset + semitones) % 12]
        
        # Plain note (C4 octave)
        mapping_data.append({
            "Sruthi": sruthi,
            "Note": note,
            "Variant": "Plain (C4)",
            "MIDI": midi,
            "Frequency (Hz)": round(freq, 2),
            "Western Note": f"{western_note}4",
            "Octave": 4
        })
        
        # Dotted Above variant (C5 octave) - add 12 semitones for one octave higher
        if base_note_letter in DOTTED_ABOVE_CHARS:
            dotted_above_char = DOTTED_ABOVE_CHARS[base_note_letter]
            dotted_above_note = dotted_above_char + variant_suffix  # e.g., Ṙ2
            semitones_above = semitones + 12  # One octave higher
            freq_above = base_freq * math.pow(2, semitones_above / 12)
            midi_above = 60 + sruthi_offset + semitones_above
            western_above = WESTERN_NOTES[(sruthi_offset + semitones_above) % 12]
            
            mapping_data.append({
                "Sruthi": sruthi,
                "Note": dotted_above_note,
                "Variant": "Dotted Above (C5)",
                "MIDI": midi_above,
                "Frequency (Hz)": round(freq_above, 2),
                "Western Note": f"{western_above}5",
                "Octave": 5
            })
        
        # Dotted Below variant (C3 octave) - subtract 12 semitones for one octave lower
        if base_note_letter in DOTTED_BELOW_CHARS:
            dotted_below_char = DOTTED_BELOW_CHARS[base_note_letter]
            dotted_below_note = dotted_below_char + variant_suffix  # e.g., Ṛ2
            semitones_below = semitones - 12  # One octave lower
            freq_below = base_freq * math.pow(2, semitones_below / 12)
            midi_below = 60 + sruthi_offset + semitones_below
            western_below = WESTERN_NOTES[(sruthi_offset + semitones_below) % 12]
            
            mapping_data.append({
                "Sruthi": sruthi,
                "Note": dotted_below_note,
                "Variant": "Dotted Below (C3)",
                "MIDI": midi_below,
                "Frequency (Hz)": round(freq_below, 2),
                "Western Note": f"{western_below}3",
                "Octave": 3
            })
    
    # Also add standalone dotted notes (without variant suffix) for backward compatibility
    # These use the base pitch of the plain note
    standalone_dotted = {
        'R': ('Ṙ', NOTE_SEMITONES['R1']),  # Use R1 as default
        'G': ('Ġ', NOTE_SEMITONES['G3']),  # Use G3 as default
        'M': ('Ṁ', NOTE_SEMITONES['M1']),  # Use M1 as default
        'D': ('Ḋ', NOTE_SEMITONES['D2']),  # Use D2 as default
        'N': ('Ṅ', NOTE_SEMITONES['N3']),  # Use N3 as default
        'S': ('Ṡ', NOTE_SEMITONES['S']),   # Use S
        'P': ('Ṗ', NOTE_SEMITONES['P']),   # Use P
    }
    
    for base_letter, (dotted_above_char, base_semitones) in standalone_dotted.items():
        if base_letter in DOTTED_BELOW_CHARS:
            dotted_below_char = DOTTED_BELOW_CHARS[base_letter]
            
            # Standalone Dotted Above (C5)
            semitones_above = base_semitones + 12
            freq_above = base_freq * math.pow(2, semitones_above / 12)
            midi_above = 60 + sruthi_offset + semitones_above
            western_above = WESTERN_NOTES[(sruthi_offset + semitones_above) % 12]
            
            mapping_data.append({
                "Sruthi": sruthi,
                "Note": dotted_above_char,  # Just Ṙ,  not Ṙ2
                "Variant": "Dotted Above (C5)",
                "MIDI": midi_above,
                "Frequency (Hz)": round(freq_above, 2),
                "Western Note": f"{western_above}5",
                "Octave": 5
            })
            
            # Standalone Dotted Below (C3)
            semitones_below = base_semitones - 12
            freq_below = base_freq * math.pow(2, semitones_below / 12)
            midi_below = 60 + sruthi_offset + semitones_below
            western_below = WESTERN_NOTES[(sruthi_offset + semitones_below) % 12]
            
            mapping_data.append({
                "Sruthi": sruthi,
                "Note": dotted_below_char,  # Just Ṛ, not Ṛ2
                "Variant": "Dotted Below (C3)",
                "MIDI": midi_below,
                "Frequency (Hz)": round(freq_below, 2),
                "Western Note": f"{western_below}3",
                "Octave": 3
            })

# Save as JSON
with open('sruthi_midi_mapping.json', 'w', encoding='utf-8') as f:
    json.dump(mapping_data, f, indent=2, ensure_ascii=False)

print(f"✅ Generated {len(mapping_data)} mapping entries")

# Verify R variants for C# sruthi
print(f"\nSample R variants for C# sruthi:")
r_variants = [m for m in mapping_data if m['Sruthi'] == 'C#' and 'R' in m['Note'] and '2' in m['Note']]
for entry in r_variants[:5]:
    print(f"  {entry['Note']}: MIDI {entry['MIDI']}, Freq {entry['Frequency (Hz)']} Hz, Variant {entry['Variant']}")

# Verify G variants for C# sruthi
print(f"\nSample G variants for C# sruthi:")
g_variants = [m for m in mapping_data if m['Sruthi'] == 'C#' and 'G' in m['Note'] and '3' in m['Note']]
for entry in g_variants[:5]:
    print(f"  {entry['Note']}: MIDI {entry['MIDI']}, Freq {entry['Frequency (Hz)']} Hz, Variant {entry['Variant']}")

# Also create CSV version
import csv
with open('sruthi_midi_mapping.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['Sruthi', 'Note', 'Variant', 'MIDI', 'Frequency (Hz)', 'Western Note', 'Octave'])
    writer.writeheader()
    writer.writerows(mapping_data)

print(f"✅ Also created CSV version ({len(mapping_data)} rows)")
