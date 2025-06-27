import re
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ReadingData:
    reading_type: str
    date: str
    heading: str
    quote: str
    source: str
    narrative: str
    affirmation: str


def parse_reading_to_dict(content: str) -> Optional[Dict[str, str]]:
    """
    Parse daily reading content and return a dictionary.
    
    Args:
        content (str): The raw text content from the daily reading file
        
    Returns:
        dict: A dictionary with parsed data, or None if parsing fails
    """
    try:
        # Extract date (format: _*June 26*_ - first occurrence of _*...*_)
        date_match = re.search(r'_\*([^*]+)\*_', content)
        date = date_match.group(1).strip() if date_match else ""

        # Extract heading (the next *...* after the date)
        all_star_matches = re.findall(r'\*([^*]+)\*', content)
        heading = all_star_matches[1].strip() if len(all_star_matches) > 1 else ""

        # Extract quote (first _..._ after heading)
        quote = ""
        if heading:
            heading_pos = content.find(heading)
            if heading_pos != -1:
                after_heading = content[heading_pos + len(heading):]
                quote_match = re.search(r'_([^_]+)_', after_heading)
                quote = quote_match.group(1).strip() if quote_match else ""
        else:
            # fallback: first _..._ anywhere
            quote_match = re.search(r'_([^_]+)_', content)
            quote = quote_match.group(1).strip() if quote_match else ""

        # Extract source (format: *– S.L.A.A. Basic Text, Page 73*)
        source_match = re.search(r'\*–\s*([^*]+)\*', content)
        source = source_match.group(1).strip() if source_match else ""

        # Extract affirmation (last *...* in the content)
        all_star_matches = re.findall(r'\*([^*]+)\*', content)
        affirmation = all_star_matches[-1].strip() if all_star_matches else ""

        # Extract narrative (text between source and affirmation)
        narrative = ""
        if source and affirmation:
            source_pos = content.find(source)
            affirmation_pos = content.find(affirmation)
            if source_pos != -1 and affirmation_pos != -1 and affirmation_pos > source_pos:
                narrative_start = source_pos + len(source) + 1
                narrative = content[narrative_start:affirmation_pos - 1].strip()
                # Clean up the narrative text
                narrative = re.sub(r'^\s*[–-]\s*', '', narrative)  # Remove leading dash
                narrative = re.sub(r'[ \t]+', ' ', narrative)  # Normalize whitespace but preserve newlines
        else:
            narrative = ""

        return {'reading_type': 'dr', 'date': date, 'heading': heading, 'quote': quote, 'source': source, 'narrative': narrative, 'affirmation': affirmation}

    except Exception as e:
        print(f"Error parsing daily reading: {e}")
        return None
