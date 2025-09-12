import re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

# def split_into_sections(text: str, headings: List[str]) -> Dict[str, str]:
#     """
#     Splits judgment text into major sections using regex on common headings.
#     Returns a dict {section_name: section_text}.
#     """

#     # Regex for splitting on headings (case-insensitive)
#     headings_pattern = "|".join(headings)
#     # 1. Pattern for SPLITTING (requires spaces + newline)
#     split_pattern = r"(" + headings_pattern + r")\s*\n"

#     # 2. Pattern for TESTING (just matches the heading itself)
#     test_pattern = r"^(" + headings_pattern + r")$"  # ^ and $ ensure exact match

#     parts = re.split(split_pattern, text, flags=re.IGNORECASE)

#     sections = {}
#     current_heading = "Header/Intro"
#     buffer = []

#     for part in parts:
#         clean = part.strip()
#         if not clean:
#             continue
#         # If matches a heading, save previous buffer
#         if re.match(test_pattern, clean, flags=re.IGNORECASE):
#             if buffer:
#                 sections[current_heading] = "\n".join(buffer).strip()
#                 buffer = []
#             current_heading = clean
#         else:
#             buffer.append(clean)

#     if buffer:
#         sections[current_heading] = "\n".join(buffer).strip()

#     return sections

def split_into_sections(html) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")
    heading_pattern = r'<p[^>]*>\s*(?:<i>\s*)?<b>[^<]*<\/b>(?:\s*<\/i>)?\s*<\/p>'
    is_judgment_found = False
    buffer = []
    sections = {}
    heading = "intro"
    for p in paragraphs:
        p_text = p.get_text().replace("\xa0", " ").strip()
        
        if p_text.lower() == "costs":
            break

        if re.match(heading_pattern, str(p)):

            if p_text.lower() == "judgment":
                is_judgment_found = True

            if is_judgment_found:
                if buffer and not (len(buffer) == 1 and buffer[0].lower() == heading) and heading != "legal context":
                    sections[heading] = "\n".join(buffer)
                buffer = []
                heading = p_text.lower()

        buffer.append(p_text)


    if buffer and not (len(buffer) == 1 and buffer[0].lower() == heading) and heading != "legal context":
        sections[heading] = "\n".join(buffer)

    return sections


# def sliding_window(text: str, max_tokens: int = 800, overlap: int = 100) -> List[str]:
#     """
#     Breaks text into overlapping chunks (by words for simplicity).
#     max_tokens ~ word count approximation (for embeddings).
#     """
#     words = text.split()
#     chunks = []
#     start = 0

#     while start < len(words):
#         end = min(start + max_tokens, len(words))
#         chunk = " ".join(words[start:end])
#         chunks.append(chunk)
#         if end == len(words):
#             break
#         start = end - overlap  # step back for overlap

#     return chunks


from typing import List

def sliding_window_preserve_lines(text: str, max_tokens: int = 800, overlap: int = 100) -> List[str]:
    """
    Break text into overlapping chunks while preserving newlines.
    Counts words approximately for max_tokens.
    
    Args:
        text: full document
        max_tokens: approx. max words per chunk
        overlap: number of words to overlap between chunks (0 = no overlap)
    """
    lines = text.splitlines(keepends=True)  # preserve \n
    chunks = []
    current_chunk = []
    word_count = 0

    for line in lines:
        line_words = len(line.split())
        
        if word_count + line_words > max_tokens:
            # finalize current chunk
            chunks.append("".join(current_chunk))
            
            # start new chunk with overlap
            overlap_words = ""
            if overlap > 0:
                overlap_words = " ".join("".join(current_chunk).split()[-overlap:])
            
            current_chunk = [overlap_words + "\n"] if overlap_words else []
            word_count = len(overlap_words.split())
        
        current_chunk.append(line)
        word_count += line_words

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks




def chunk_judgment(html: str, max_tokens: int = 800, overlap: int = 100) -> List[Dict]:
    """
    Full pipeline:
    1. Split judgment into sections
    2. Apply sliding-window splitting inside each section if too long
    3. Return list of chunks with metadata
    """
    sections = split_into_sections(html)
    all_chunks = []

    for sec_name, sec_text in sections.items():
        # windows = sliding_window_preserve_lines(sec_text, max_tokens=max_tokens, overlap=overlap)
        windows = spacy_sentence_chunker(sec_text, max_tokens=max_tokens, overlap=overlap)
        for i, chunk in enumerate(windows):
            all_chunks.append({
                "section": sec_name,
                "chunk_id": f"{sec_name}_{i+1}",
                "text": chunk
            })

    return all_chunks



from typing import List
import spacy

# Load spaCy once (small = fast; transformer = more accurate)
nlp = spacy.load("en_core_web_sm")

def spacy_sentence_chunker(
    text: str,
    max_tokens: int = 800,
    overlap: int = 100
) -> List[str]:
    """
    Split text into chunks based on sentences using spaCy.

    Args:
        text: The input document.
        max_tokens: Approximate max words per chunk.
        overlap: Number of words to overlap between consecutive chunks.

    Returns:
        List of chunk strings.
    """
    if not text.strip():
        return [""]

    # doc = nlp(text)
    # sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    import spacy
    from spacy.lang.en import English

    nlp = English()
    nlp.add_pipe("sentencizer")  # rule-based
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]

    chunks = []
    current_chunk = []
    word_count = 0

    for sent in sentences:
        sent_len = len(sent.split())

        if word_count + sent_len > max_tokens and current_chunk:
            # finalize current chunk
            chunks.append(" ".join(current_chunk))

            # prepare overlap
            overlap_tokens = []
            if overlap > 0:
                last_chunk_words = " ".join(current_chunk).split()
                overlap_tokens = last_chunk_words[-overlap:]

            current_chunk = overlap_tokens.copy()
            word_count = len(overlap_tokens)

        current_chunk.append(sent)
        word_count += sent_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
