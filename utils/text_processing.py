import re
from typing import List

def chunk_text(text: str, max_chars: int = 1000, overlap: int = 100) -> List[str]:
    """
    Chunks text strictly by character limit to respect Embedding context windows (usually 512 tokens ~ 2000 chars).
    Splits by double newline, then single newline, then sentence period, then forceful slice.
    """
    if not text:
        return []
        
    chunks = []
    
    # 1. Normalize
    text = text.replace("\r\n", "\n")
    
    # 2. Recursive split helper
    def recursive_split(text_segment):
        if len(text_segment) <= max_chars:
            return [text_segment]
            
        # Try splitting by paragraph
        separators = ["\n\n", "\n", ". ", " "]
        for sep in separators:
            parts = text_segment.split(sep)
            # If split didn't help (still 1 part), try next separator
            if len(parts) == 1:
                continue
                
            # Re-assemble suitable chunks
            sub_chunks = []
            current = ""
            for p in parts:
                candidate = current + (sep if current else "") + p
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        sub_chunks.append(current)
                    current = p
            if current:
                sub_chunks.append(current)
            
            # If we successfully broke it down, return these (recurse checking if any are STILL too big? 
            # Logic above re-assembles to max_chars, so assuming atomic parts < max_chars. 
            # If a single part > max_chars even after space split, we force slice.)
            
            final_result = []
            for c in sub_chunks:
                if len(c) > max_chars:
                    # Force slice (brute force)
                    for i in range(0, len(c), max_chars - overlap):
                        final_result.append(c[i:i + max_chars])
                else:
                    final_result.append(c)
            return final_result
            
        # If no separators work (e.g. giant string of diff chars), force slice
        return [text_segment[i:i + max_chars] for i in range(0, len(text_segment), max_chars - overlap)]

    return recursive_split(text)
