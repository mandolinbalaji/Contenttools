#!/usr/bin/env python3
"""
MIDI file analyzer to validate MIDI structure and timing
"""

import sys
import struct

def analyze_midi(filename):
    """Analyze MIDI file structure"""
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"MIDI File Size: {len(data)} bytes")
    print(f"First 20 bytes (hex): {data[:20].hex()}")
    print()
    
    idx = 0
    
    # Check header
    if data[0:4] != b'MThd':
        print("ERROR: Missing MThd header!")
        return
    
    print("✓ MThd header found")
    
    # Header length (should be 6)
    header_len = struct.unpack('>I', data[4:8])[0]
    print(f"  Header length: {header_len} bytes")
    
    # Format, tracks, TPQN
    format_type = struct.unpack('>H', data[8:10])[0]
    num_tracks = struct.unpack('>H', data[10:12])[0]
    tpqn = struct.unpack('>H', data[12:14])[0]
    
    print(f"  Format: {format_type}")
    print(f"  Tracks: {num_tracks}")
    print(f"  TPQN (Ticks Per Quarter Note): {tpqn}")
    print()
    
    if tpqn != 480:
        print(f"  ⚠️  TPQN is {tpqn}, typically should be 480 or 960")
    
    # Now check track data
    idx = 14
    
    for track_num in range(num_tracks):
        if idx + 8 > len(data):
            print(f"ERROR: Not enough data for track {track_num}")
            return
        
        # Check MTrk header
        if data[idx:idx+4] != b'MTrk':
            print(f"ERROR: Missing MTrk header for track {track_num} at offset {idx}")
            return
        
        track_len = struct.unpack('>I', data[idx+4:idx+8])[0]
        print(f"✓ Track {track_num}: MTrk header found")
        print(f"  Track length: {track_len} bytes")
        
        idx += 8
        track_end = idx + track_len
        
        # Analyze events in track
        event_count = 0
        prev_time = 0
        total_time = 0
        
        while idx < track_end:
            if idx + 1 > len(data):
                break
            
            # Read variable length quantity
            delta_time, vlen_len = read_variable_length(data, idx)
            idx += vlen_len
            total_time += delta_time
            
            if idx >= track_end:
                break
            
            event_type = data[idx]
            idx += 1
            event_count += 1
            
            if event_type == 0xFF:  # Meta event
                if idx >= len(data):
                    break
                meta_type = data[idx]
                idx += 1
                
                length, vlen_len = read_variable_length(data, idx)
                idx += vlen_len
                
                if meta_type == 0x51:  # Tempo
                    tempo_us_per_qn = struct.unpack('>I', b'\x00' + data[idx:idx+3])[0]
                    bpm = 60_000_000 / tempo_us_per_qn
                    print(f"  Event {event_count}: Tempo - {bpm:.1f} BPM ({tempo_us_per_qn} µs/QN)")
                elif meta_type == 0x59:  # Key signature
                    sharps = struct.unpack('>b', data[idx:idx+1])[0]
                    minor = data[idx+1]
                    print(f"  Event {event_count}: Key Signature - {sharps} sharps, minor={minor}")
                elif meta_type == 0x03:  # Sequence name
                    name = data[idx:idx+length].decode('utf-8', errors='ignore')
                    print(f"  Event {event_count}: Sequence Name (Title) - '{name}'")
                elif meta_type == 0x04:  # Track name
                    name = data[idx:idx+length].decode('utf-8', errors='ignore')
                    print(f"  Event {event_count}: Track Name - '{name}'")
                elif meta_type == 0x05:  # Lyric
                    lyric = data[idx:idx+length].decode('utf-8', errors='ignore')
                    print(f"  Event {event_count}: Lyric - '{lyric}'")
                elif meta_type == 0x01:  # Text
                    text = data[idx:idx+length].decode('utf-8', errors='ignore')
                    print(f"  Event {event_count}: Text - '{text}'")
                elif meta_type == 0x2F:  # End of track
                    print(f"  Event {event_count}: End of Track")
                else:
                    print(f"  Event {event_count}: Meta {hex(meta_type)} (len={length})")
                
                idx += length
            
            elif event_type in [0x90, 0x80]:  # Note on/off
                if idx + 2 > len(data):
                    break
                
                note = data[idx]
                velocity = data[idx+1]
                idx += 2
                
                event_name = "Note On" if event_type == 0x90 else "Note Off"
                print(f"  Event {event_count}: {event_name} - Note {note}, Velocity {velocity}, Delta={delta_time}")
            
            elif event_type == 0xB0:  # Control change
                if idx + 2 > len(data):
                    break
                idx += 2
                print(f"  Event {event_count}: Control Change, Delta={delta_time}")
            else:
                print(f"  Event {event_count}: Unknown event type {hex(event_type)}, Delta={delta_time}")
        
        print(f"  Total events in track: {event_count}")
        print(f"  Total duration: {total_time} ticks ({total_time / tpqn:.2f} quarter notes)")
        print()
        
        idx = track_end


def read_variable_length(data, start_idx):
    """Read a variable-length quantity from MIDI data"""
    value = 0
    idx = start_idx
    
    while idx < len(data):
        byte = data[idx]
        value = (value << 7) | (byte & 0x7F)
        idx += 1
        
        if not (byte & 0x80):
            break
    
    return value, idx - start_idx


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python midi_analyzer.py <midi_file>")
        sys.exit(1)
    
    analyze_midi(sys.argv[1])
