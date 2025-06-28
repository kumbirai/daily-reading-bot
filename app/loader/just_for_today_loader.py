import re
from dataclasses import dataclass
from typing import Dict, \
    Optional


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
    Parse Just For Today reading content and return a dictionary.
    
    Args:
        content (str): The raw text content from the Just For Today file
        
    Returns:
        dict: A dictionary with parsed data, or None if parsing fails
    """
    try:
        # Extract date (format: _*June 26*_)
        date_match = re.search(r'_\*([^*]+)\*_',
                               content)
        date = date_match.group(1).strip() if date_match else ""

        # Extract heading (third *...* match: "Just For Today", date, then heading)
        all_star_matches = re.findall(r'\*([^*]+)\*',
                                      content)
        heading = ""
        if len(all_star_matches) > 2:
            # Skip "Just For Today" and date, get the third one (heading)
            heading = all_star_matches[2].strip()

        # Extract quote (first _..._ after heading)
        quote = ""
        if heading:
            heading_pos = content.find(heading)
            if heading_pos != -1:
                after_heading = content[heading_pos + len(heading):]
                quote_match = re.search(r'_([^_]+)_',
                                        after_heading)
                quote = quote_match.group(1).strip() if quote_match else ""
        else:
            # fallback: first _..._ anywhere
            quote_match = re.search(r'_([^_]+)_',
                                    content)
            quote = quote_match.group(1).strip() if quote_match else ""

        # Extract source (next *...* after quote)
        source = ""
        if quote:
            quote_pos = content.find(quote)
            if quote_pos != -1:
                after_quote = content[quote_pos + len(quote):]
                source_match = re.search(r'\*([^*]+)\*',
                                         after_quote)
                source = source_match.group(1).strip() if source_match else ""

        # Extract affirmation (text between last *...* and end of document)
        # Find the last *...* match
        all_star_matches = re.findall(r'\*([^*]+)\*',
                                      content)
        last_star_content = all_star_matches[-1].strip() if all_star_matches else ""

        # Find the position of the last *...* and get everything after it
        last_star_pos = content.rfind(last_star_content)
        if last_star_pos != -1:
            affirmation_start = last_star_pos + len(last_star_content) + 1
            affirmation = content[affirmation_start:].strip()
            # Clean up the affirmation text
            affirmation = re.sub(r'^\s*[–-]\s*',
                                 '',
                                 affirmation)  # Remove leading dash
            affirmation = re.sub(r'\s+',
                                 ' ',
                                 affirmation)  # Normalize whitespace
        else:
            affirmation = ""

        # Extract narrative (text between source and affirmation)
        narrative = ""
        if source and affirmation:
            source_pos = content.find(source)
            if source_pos != -1:
                # Find the start of the narrative (after source)
                narrative_start = source_pos + len(source) + 1
                # Find the end of narrative (before the last *...*)
                last_star_pos = content.rfind(last_star_content) - 1
                if last_star_pos > narrative_start:
                    narrative = content[narrative_start:last_star_pos].strip()
                    # Clean up the narrative text
                    narrative = re.sub(r'^\s*[–-]\s*',
                                       '',
                                       narrative)  # Remove leading dash
                    narrative = re.sub(r'[ \t]+',
                                       ' ',
                                       narrative)  # Normalize whitespace but preserve newlines
        else:
            narrative = ""

        return {
            'reading_type': 'jft',
            'date': date,
            'heading': heading,
            'quote': quote,
            'source': source,
            'narrative': narrative,
            'affirmation': affirmation}

    except Exception as e:
        print(f"Error parsing Just For Today reading: {e}")
        return None
