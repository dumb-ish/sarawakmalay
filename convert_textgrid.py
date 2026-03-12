import json
import os
import sys
from pathlib import Path

def parse_textgrid_file(textgrid_path):
    """Parse a TextGrid file and convert to the target format."""
    segments = []
    
    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252']
    lines = None
    
    for encoding in encodings:
        try:
            with open(textgrid_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    
    if lines is None:
        print(f"Could not read file {textgrid_path} with available encodings")
        return segments
    
    # Find the Speaker tier section
    speaker_tier_start = -1
    speaker_tier_end = -1
    
    for i, line in enumerate(lines):
        if 'name = "Speaker"' in line:
            # Find the start of the intervals section for this tier
            for j in range(i, len(lines)):
                if 'intervals: size =' in lines[j]:
                    size_line = lines[j]
                    size = int(size_line.split('=')[1].strip())
                    speaker_tier_start = j
                    speaker_tier_end = j + size * 3  # Each interval takes ~3 lines
                    break
            break
    
    if speaker_tier_start == -1:
        return segments
    
    # Collect unique speakers to assign indices
    unique_speakers = []
    
    # First pass: find all unique speakers in the Speaker tier
    for i in range(speaker_tier_start + 1, min(speaker_tier_end + 100, len(lines))):
        if 'text = "' in lines[i]:
            text_line = lines[i].strip()
            start_quote = text_line.find('"')
            end_quote = text_line.rfind('"')
            if start_quote != -1 and end_quote != -1 and start_quote != end_quote:
                speaker_text = text_line[start_quote+1:end_quote]
                if speaker_text and speaker_text not in unique_speakers:
                    unique_speakers.append(speaker_text)
    
    # Now find the Sarawak tier (transcription tier)
    sarawak_tier_start = -1
    sarawak_tier_end = -1
    
    for i, line in enumerate(lines):
        if 'name = "Sarawak"' in line:
            # Find the start of the intervals section for this tier
            for j in range(i, len(lines)):
                if 'intervals: size =' in lines[j]:
                    size_line = lines[j]
                    size = int(size_line.split('=')[1].strip())
                    sarawak_tier_start = j
                    sarawak_tier_end = j + size * 3
                    break
            break
    
    if sarawak_tier_start == -1:
        return segments
    
    # Process both tiers together
    sarawak_intervals = []
    speaker_intervals = []
    
    # Extract Sarawak intervals
    interval_count = 0
    max_intervals = 0
    # Count total intervals in this tier
    for line in lines[sarawak_tier_start:]:
        if 'intervals [' in line:
            max_intervals += 1
        elif 'intervals: size =' in line:
            size = int(line.split('=')[1].strip())
            max_intervals = size
            break
    
    for i in range(sarawak_tier_start + 1, len(lines)):
        if 'intervals [' in lines[i]:
            interval_count += 1
        elif 'xmin =' in lines[i] and 'xmax =' in lines[i+1] and 'text =' in lines[i+2]:
            xmin_line = lines[i].strip()
            xmax_line = lines[i+1].strip()
            text_line = lines[i+2].strip()
            
            xmin = float(xmin_line.split('=')[1].strip())
            xmax = float(xmax_line.split('=')[1].strip())
            
            start_quote = text_line.find('"')
            end_quote = text_line.rfind('"')
            if start_quote != -1 and end_quote != -1 and start_quote != end_quote:
                text = text_line[start_quote+1:end_quote]
            else:
                text = ""
            
            sarawak_intervals.append((xmin, xmax, text))
            
            if interval_count >= max_intervals:
                break
    
    # Extract Speaker intervals
    interval_count = 0
    max_intervals = 0
    # Count total intervals in this tier
    for line in lines[speaker_tier_start:]:
        if 'intervals [' in line:
            max_intervals += 1
        elif 'intervals: size =' in line:
            size = int(line.split('=')[1].strip())
            max_intervals = size
            break
    
    for i in range(speaker_tier_start + 1, len(lines)):
        if 'intervals [' in lines[i]:
            interval_count += 1
        elif 'xmin =' in lines[i] and 'xmax =' in lines[i+1] and 'text =' in lines[i+2]:
            xmin_line = lines[i].strip()
            xmax_line = lines[i+1].strip()
            text_line = lines[i+2].strip()
            
            xmin = float(xmin_line.split('=')[1].strip())
            xmax = float(xmax_line.split('=')[1].strip())
            
            start_quote = text_line.find('"')
            end_quote = text_line.rfind('"')
            if start_quote != -1 and end_quote != -1 and start_quote != end_quote:
                text = text_line[start_quote+1:end_quote]
            else:
                text = ""
            
            speaker_intervals.append((xmin, xmax, text))
            
            if interval_count >= max_intervals:
                break
    
    # Combine the intervals, keeping only those with non-empty text
    for i in range(min(len(sarawak_intervals), len(speaker_intervals))):
        sarawak_xmin, sarawak_xmax, sarawak_text = sarawak_intervals[i]
        speaker_xmin, speaker_xmax, speaker_text = speaker_intervals[i]
        
        # Only add segments that have actual text content
        if sarawak_text.strip() and speaker_text.strip():
            # Assign speaker index based on position in unique_speakers list
            if speaker_text in unique_speakers:
                speaker_index = unique_speakers.index(speaker_text)
                speaker_letter = chr(ord('A') + speaker_index)  # A, B, C, etc.
                
                segment = {
                    "start": sarawak_xmin,
                    "end": sarawak_xmax,
                    "speaker": speaker_letter,
                    "speaker_label": speaker_text,
                    "raw_text": sarawak_text,
                    "processed_transcript": sarawak_text,
                    "language": "ms",  # Set language to Malay based on content
                    "keyword": [],
                    "estimated_snr": 0
                }
                segments.append(segment)
    
    return segments

def create_output_structure(textgrid_files):
    """Create the complete output structure."""
    dataset_info = {
        "dataset": {
            "dataset_name": "Malay Conversation Dataset v1",
            "dataset_description": "Malay conversation data for speech recognition",
            "dataset_task": "Automatic Speech Recognition (ASR) for Malay conversations"
        },
        "ground_truth": []
    }
    
    for textgrid_path in textgrid_files:
        textgrid_file = Path(textgrid_path)
        
        # Create corresponding WAV filename
        wav_filename = textgrid_file.stem + ".wav"
        
        # For file size, we'll set a placeholder since no actual file exists
        file_size = 0  # You can modify this if you have actual audio files
        
        # Get segments from the TextGrid file
        segments = parse_textgrid_file(textgrid_path)
        
        entry = {
            "filename": f"audio/{wav_filename}",
            "file-metadata": {
                "original_name": wav_filename,
                "file_size": file_size
            },
            "segments": segments
        }
        
        dataset_info["ground_truth"].append(entry)
    
    return dataset_info

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_textgrid.py <textgrid_file1> [textgrid_file2] ...")
        print("Or provide directory containing .TextGrid files")
        return
    
    input_paths = sys.argv[1:]
    textgrid_files = []
    
    for path in input_paths:
        path_obj = Path(path)
        if path_obj.is_dir():
            # Get all .TextGrid files in the directory (case insensitive)
            textgrid_files.extend([f for f in path_obj.glob("*.TextGrid")] + 
                                 [f for f in path_obj.glob("*.textgrid")] +
                                 [f for f in path_obj.glob("*.TEXTGRID")])
        elif path_obj.is_file() and path_obj.suffix.lower() in ['.textgrid']:
            textgrid_files.append(path_obj)
    
    if not textgrid_files:
        print("No .TextGrid files found!")
        return
    
    # Create the output structure
    result = create_output_structure(textgrid_files)
    
    # Write to output JSON file
    output_file = "converted_textgrid_dataset.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    
    print(f"Conversion completed! Output saved to {output_file}")
    print(f"Processed {len(textgrid_files)} TextGrid files")
    total_segments = sum(len(entry['segments']) for entry in result['ground_truth'])
    print(f"Total segments created: {total_segments}")

if __name__ == "__main__":
    main()