#!/usr/bin/env python3
import json

# Load Swaratest.json
with open('songs/Swaratest.json', 'r', encoding='utf-8') as f:
    song = json.load(f)

print("=== PRE-ENRICHMENT ATOM STRUCTURE ===\n")

# Get first PDMP atom 
found = False
for section in song.get('sections', []):
    for row in section.get('rows', []):
        atoms = row.get('atoms', [])
        for atom in atoms:
            if isinstance(atom, dict) and atom.get('text') == 'PDMP' and not found:
                print(f"PDMP Atom (before enrichment):")
                print(f"  text: {atom.get('text')}")
                print(f"  speed: {atom.get('speed')}")
                print(f"  midiNumber type: {type(atom.get('midiNumber')).__name__}")
                print(f"  midiNumber: {atom.get('midiNumber')}")
                print(f"  ragaswaraEquivalent type: {type(atom.get('ragaswaraEquivalent')).__name__}")
                print(f"  ragaswaraEquivalent: {atom.get('ragaswaraEquivalent')}")
                print(f"  frequency: {atom.get('frequency')}")
                print()
                found = True
                break

# Get another multi-char example
found_sr = False
for section in song.get('sections', []):
    for row in section.get('rows', []):
        atoms = row.get('atoms', [])
        for atom in atoms:
            if isinstance(atom, dict) and atom.get('text') == 'SR3' and not found_sr:
                print(f"SR3 Atom (before enrichment):")
                print(f"  text: {atom.get('text')}")
                print(f"  midiNumber type: {type(atom.get('midiNumber')).__name__}")
                print(f"  midiNumber: {atom.get('midiNumber')}")
                print(f"  ragaswaraEquivalent type: {type(atom.get('ragaswaraEquivalent')).__name__}")
                print(f"  ragaswaraEquivalent: {atom.get('ragaswaraEquivalent')}")
                print()
                found_sr = True
                break

print("\n=== EXPECTED AFTER ENRICHMENT ===\n")
print("PDMP should become:")
print("  midiNumber: [68, 70, 66, 68]")
print("  ragaswaraEquivalent: ['p', 'd2', 'm1', 'p']")
print("  frequency: [415.3, 466.16, 369.99, 415.3]")
print()
print("SR3 should become:")
print("  midiNumber: [61, 64]")
print("  ragaswaraEquivalent: ['s', 'r3']")
print("  frequency: [277.18, 329.62]")
