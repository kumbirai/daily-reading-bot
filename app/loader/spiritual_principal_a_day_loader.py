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
    Parse Spiritual Principal a Day reading content and return a dictionary.
    
    Args:
        content (str): The raw text content from the daily reading file
        
    Returns:
        dict: A dictionary with parsed data, or None if parsing fails
    """
    try:
        # Extract date (format: _*June 26*_)
        date_match = re.search(r'_\*([^*]+)\*_', content)
        date = date_match.group(1).strip() if date_match else ""

        # Extract heading (third *...* match: "Spiritual Principle A Day", date, then heading)
        all_star_matches = re.findall(r'\*([^*]+)\*', content)
        heading = ""
        if len(all_star_matches) > 2:
            # Skip "Spiritual Principle A Day" and date, get the third one (heading)
            heading = all_star_matches[2].strip()

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

        # Extract source (next *...* after quote)
        source = ""
        if quote:
            quote_pos = content.find(quote)
            if quote_pos != -1:
                after_quote = content[quote_pos + len(quote):]
                source_match = re.search(r'\*([^*]+)\*', after_quote)
                source = source_match.group(1).strip() if source_match else ""

        # Extract affirmation (text between the last _..._)
        all_underscore_matches = re.findall(r'_([^_]+)_', content)
        affirmation = ""
        if len(all_underscore_matches) > 1:
            # Get the last _..._ match
            affirmation = all_underscore_matches[-1].strip()

        # Extract narrative (text between source and affirmation)
        narrative = ""
        if source and affirmation:
            source_pos = content.find(source)
            if source_pos != -1:
                # Find the start of the narrative (after source)
                narrative_start = source_pos + len(source) + 1
                # Find the end of narrative (before the last _..._)
                last_underscore_pos = content.rfind(affirmation) - 1
                if last_underscore_pos > narrative_start:
                    narrative = content[narrative_start:last_underscore_pos].strip()
                    # Clean up the narrative text
                    narrative = re.sub(r'^\s*[–-]\s*', '', narrative)  # Remove leading dash
                    narrative = re.sub(r'[ \t]+', ' ', narrative)  # Normalize whitespace but preserve newlines
        else:
            narrative = ""

        return {'reading_type': 'spad', 'date': date, 'heading': heading, 'quote': quote, 'source': source, 'narrative': narrative, 'affirmation': affirmation}

    except Exception as e:
        print(f"Error parsing Spiritual Principal a Day reading: {e}")
        return None
