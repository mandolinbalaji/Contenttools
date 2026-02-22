#!/usr/bin/env python3
"""
Spreadsheet Converter for Music Notation
Converts between JSON notation format and CSV/Google Sheets format
"""

import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any

class NotationSpreadsheetConverter:
    """Convert music notation between JSON and CSV formats"""
    
    def __init__(self, json_file: str = "notation-composer.json"):
        self.json_file = Path(json_file)
        self.csv_file = self.json_file.with_stem(self.json_file.stem + "_spreadsheet").with_suffix('.csv')
        self.data = []
    
    def load_json(self) -> List[Dict[str, Any]]:
        """Load notation data from JSON file"""
        with open(self.json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        print(f"✓ Loaded {len(self.data)} songs from {self.json_file}")
        return self.data
    
    def export_to_csv_spreadsheet_format(self, output_csv: str = None, song_name: str = None) -> str:
        """
        Export notation data as visual spreadsheet (one atom per column)
        Matches the HTML notation table layout:
        - Metadata row at top
        - Section title rows
        - Swara rows (one atom per column)
        - Lyric rows (one atom per column)
        """
        if not self.data:
            self.load_json()
        
        output_file = output_csv
        
        # Filter songs if song_name specified
        songs_to_export = self.data
        if song_name:
            songs_to_export = [s for s in self.data if song_name.lower() in s.get('name', '').lower()]
            if not songs_to_export:
                print(f"⚠️ No songs found matching: {song_name}")
                return output_file
        
        if len(songs_to_export) > 1:
            print(f"⚠️ Multiple songs found. Exporting first match: {songs_to_export[0].get('name')}")
        
        song = songs_to_export[0]
        
        rows = []
        
        # Metadata section
        rows.append(['SONG METADATA'])
        rows.append(['Name:', song.get('name', '')])
        rows.append(['Ragam:', song.get('ragam', '')])
        rows.append(['Composer:', song.get('composer', '')])
        rows.append(['Tala:', f"{song.get('beats', '')}/{song.get('nadai', '')}", 'Eduppu:', song.get('eduppu', '')])
        rows.append(['BPM:', song.get('bpm', ''), 'Arohana:', song.get('arohana', '')])
        rows.append(['Avarohana:', song.get('avarohana', '')])
        rows.append([])  # Blank row
        
        # Sections
        for section in song.get('sections', []):
            rows.append([f"SECTION: {section.get('title', '')}", 'ROW TYPE', 'CONTENT'])
            rows.append([])  # Blank row separator
            
            for row in section.get('rows', []):
                row_type = 'SWARA' if row.get('type') == 'swara' else 'LYRIC'
                atoms = row.get('atoms', [])
                
                # Create row with atom contents
                atom_row = [row_type]
                for atom in atoms:
                    if isinstance(atom, dict):
                        text = atom.get('text', '')
                        speed = atom.get('speed', 1)
                        # Mark braced notes with 2× suffix ONLY on SWARA rows (keep orange badge style)
                        if speed == 2 and row_type == 'SWARA':
                            text = f"{text} 2×"
                        atom_row.append(text)
                    else:
                        atom_row.append(str(atom))
                
                rows.append(atom_row)
            
            rows.append([])  # Blank row between sections
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        print(f"✓ Exported as spreadsheet format: {output_file}")
        print(f"  Layout: Visual columns matching notation grid")
        return output_file
        """
        Export notation data to CSV suitable for Google Sheets
        Each song becomes a group of rows
        Optionally filter by song name
        """
        if not self.data:
            self.load_json()
        
        output_file = flattened_csv or str(self.csv_file)
        
        # Filter songs if song_name specified
        songs_to_export = self.data
        if song_name:
            songs_to_export = [s for s in self.data if song_name.lower() in s.get('name', '').lower()]
            if not songs_to_export:
                print(f"⚠️ No songs found matching: {song_name}")
                return output_file
        
        rows = []
        
        for song_idx, song in enumerate(songs_to_export):
            # Song metadata row
            rows.append({
                'SONG_NUM': song_idx + 1,
                'NAME': song.get('name', ''),
                'RAGAM': song.get('ragam', ''),
                'COMPOSER': song.get('composer', ''),
                'BEATS': song.get('beats', ''),
                'NADAI': song.get('nadai', ''),
                'BPM': song.get('bpm', ''),
                'EDUPPU': song.get('eduppu', ''),
                'AROHANA': song.get('arohana', ''),
                'AVAROHANA': song.get('avarohana', ''),
                'NOTATION_SOURCE': song.get('notation', ''),
                'ROW_TYPE': 'METADATA',
                'SECTION': '',
                'NOTATION_STRING': '',
                'ATOM_DATA': ''
            })
            
            # Section and notation rows
            for section in song.get('sections', []):
                for row in section.get('rows', []):
                    atoms = row.get('atoms', [])
                    atom_string = ''
                    for atom in atoms:
                        if isinstance(atom, dict):
                            atom_string += atom.get('text', '')
                        else:
                            atom_string += str(atom)
                    
                    rows.append({
                        'SONG_NUM': song_idx + 1,
                        'NAME': song.get('name', ''),
                        'RAGAM': song.get('ragam', ''),
                        'COMPOSER': song.get('composer', ''),
                        'BEATS': song.get('beats', ''),
                        'NADAI': song.get('nadai', ''),
                        'BPM': song.get('bpm', ''),
                        'EDUPPU': song.get('eduppu', ''),
                        'AROHANA': song.get('arohana', ''),
                        'AVAROHANA': song.get('avarohana', ''),
                        'NOTATION_SOURCE': song.get('notation', ''),
                        'ROW_TYPE': 'SWARA' if row.get('type') == 'swara' else 'LYRIC',
                        'SECTION': section.get('title', ''),
                        'NOTATION_STRING': atom_string,
                        'ATOM_DATA': json.dumps(row.get('atoms', []))
                    })
        
        # Write to CSV
        fieldnames = [
            'SONG_NUM', 'NAME', 'RAGAM', 'COMPOSER', 'BEATS', 'NADAI', 'BPM', 
            'EDUPPU', 'AROHANA', 'AVAROHANA', 'NOTATION_SOURCE',
            'ROW_TYPE', 'SECTION', 'NOTATION_STRING', 'ATOM_DATA'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✓ Exported to CSV: {output_file}")
        print(f"  Total rows: {len(rows)}")
        return output_file
    
    def import_from_csv(self, csv_file: str, output_json: str = None) -> str:
        """
        Import notation data from CSV (e.g., from Google Sheets export)
        Reconstructs JSON format from flattened CSV
        """
        output_file = output_json or str(self.json_file.with_stem(self.json_file.stem + "_imported"))
        
        songs_dict = {}
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                song_num = int(row.get('SONG_NUM', 0))
                
                if song_num not in songs_dict:
                    songs_dict[song_num] = {
                        'name': row.get('NAME', ''),
                        'ragam': row.get('RAGAM', ''),
                        'composer': row.get('COMPOSER', ''),
                        'beats': row.get('BEATS', ''),
                        'nadai': row.get('NADAI', ''),
                        'bpm': row.get('BPM', ''),
                        'eduppu': row.get('EDUPPU', ''),
                        'arohana': row.get('AROHANA', ''),
                        'avarohana': row.get('AVAROHANA', ''),
                        'notation': row.get('NOTATION_SOURCE', ''),
                        'sections': []
                    }
                
                row_type = row.get('ROW_TYPE', '')
                section_title = row.get('SECTION', '')
                
                if row_type in ['SWARA', 'LYRIC']:
                    # Find or create section
                    song_data = songs_dict[song_num]
                    section = None
                    
                    for s in song_data['sections']:
                        if s.get('title') == section_title:
                            section = s
                            break
                    
                    if not section:
                        section = {'title': section_title, 'rows': []}
                        song_data['sections'].append(section)
                    
                    # Add row if not already there
                    atom_data_str = row.get('ATOM_DATA', '[]')
                    try:
                        atoms = json.loads(atom_data_str)
                    except:
                        atoms = []
                    
                    if atoms:
                        new_row = {
                            'type': 'swara' if row_type == 'SWARA' else 'lyric',
                            'atoms': atoms
                        }
                        
                        # Check if this exact row already exists
                        row_exists = False
                        for existing_row in section['rows']:
                            if existing_row.get('type') == new_row['type']:
                                row_exists = True
                                break
                        
                        if not row_exists:
                            section['rows'].append(new_row)
        
        # Convert dict to list and write JSON
        result = [songs_dict[k] for k in sorted(songs_dict.keys())]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Imported from CSV: {csv_file}")
        print(f"✓ Created JSON: {output_file}")
        print(f"  Total songs: {len(result)}")
        return output_file


def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert music notation between JSON and CSV formats')
    parser.add_argument('--export', action='store_true', help='Export JSON to CSV (for Google Sheets)')
    parser.add_argument('--format', choices=['spreadsheet', 'flat'], default='spreadsheet',
                        help='Export format: spreadsheet (visual layout) or flat (JSON data)')
    parser.add_argument('--import', dest='import_csv', help='Import CSV file (from Google Sheets) and convert to JSON')
    parser.add_argument('--json', default='notation-composer.json', help='JSON file path (default: notation-composer.json)')
    parser.add_argument('--csv', help='CSV file path (optional)')
    parser.add_argument('--output', help='Output file path (optional)')
    parser.add_argument('--song', help='Filter export by song name (optional, case-insensitive partial match)')
    
    args = parser.parse_args()
    
    converter = NotationSpreadsheetConverter(args.json)
    
    if args.export:
        converter.load_json()
        
        if args.format == 'spreadsheet':
            output_csv = args.csv or (f"notation-composer_{args.song}_spreadsheet.csv" if args.song 
                                      else "notation-composer_spreadsheet.csv")
            converter.export_to_csv_spreadsheet_format(output_csv, song_name=args.song)
        else:
            output_csv = args.csv or (f"notation-composer_{args.song}.csv" if args.song 
                                      else "notation-composer.csv")
            converter.export_to_csv(output_csv, song_name=args.song)
        
        print("\n📊 CSV file created successfully!")
        print(f"   Upload to Google Sheets at: https://sheets.google.com")
        print(f"   File: {output_csv}")
    
    elif args.import_csv:
        if not Path(args.import_csv).exists():
            print(f"❌ CSV file not found: {args.import_csv}")
            sys.exit(1)
        converter.import_from_csv(args.import_csv, args.output)
        print("\n✅ Import completed successfully!")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
