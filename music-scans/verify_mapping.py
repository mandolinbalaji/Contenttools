import json

data = json.load(open('sruthi_midi_mapping.json', 'r', encoding='utf-8'))

# Check Ṙ variants (both standalone and with suffixes)
print(f'Checking C# Ṙ variants:')
r_all = [m for m in data if m['Sruthi'] == 'C#' and 'Ṙ' in m['Note']]
for m in sorted(r_all, key=lambda x: x['MIDI']):
    print(f"  {m['Note']}: MIDI {m['MIDI']}, Freq {m['Frequency (Hz)']} Hz, {m['Variant']}")
print(f'Total Ṙ entries for C#: {len(r_all)}')

# Check standalone Ṙ (without suffix)
standalone_r = [m for m in data if m['Sruthi'] == 'C#' and m['Note'] == 'Ṙ']
print(f'\nStandalone Ṙ entries: {len(standalone_r)}')
for m in standalone_r:
    print(f"  {m['Note']}: MIDI {m['MIDI']}, Freq {m['Frequency (Hz)']} Hz, {m['Variant']}")

# Check Ġ variants
print(f'\nChecking C# Ġ variants:')
g_all = [m for m in data if m['Sruthi'] == 'C#' and 'Ġ' in m['Note']]
for m in sorted(g_all, key=lambda x: x['MIDI']):
    print(f"  {m['Note']}: MIDI {m['MIDI']}, Freq {m['Frequency (Hz)']} Hz, {m['Variant']}")
print(f'Total Ġ entries for C#: {len(g_all)}')

# Check total entries
print(f'\nTotal entries: {len(data)}')
print(f'Entries per sruthi: {len(data) // 12}')

