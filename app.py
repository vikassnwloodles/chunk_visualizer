import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict

st.set_page_config(page_title="Judgment Chunk Visualizer", layout="wide")
st.title("📑 Judgment Chunk Visualizer")

# ----------------------------
# Sidebar configuration
# ----------------------------
st.sidebar.header("Settings")

page_id = st.sidebar.text_input("HTML element id", value="document_content")
max_tokens = st.sidebar.number_input("Max words per chunk", value=500, min_value=50, max_value=5000)
overlap = st.sidebar.number_input("Overlap words", value=0, min_value=0, max_value=1000)

# headings_raw = st.sidebar.text_area(
#     "Headings (regex, one per line)",
#     value="\n".join([
#         "Judgment",
#         "Legal context",
#         "The disputes? in the main proceedings? and the questions? referred for a preliminary ruling",
#         "Procedure before the Court",
#         "Admissibility of the requests for a preliminary ruling",
#         "The .* questions?",
#         "Costs"
#     ])
# )
# headings = [h.strip() for h in headings_raw.splitlines() if h.strip()]
headings = [
    "Judgment",
    "Legal context",
    "The disputes? in the main proceedings? and the questions? referred for a preliminary ruling",
    "Procedure before the Court",
    "Admissibility of the requests for a preliminary ruling",
    "The .* questions?",
    "Costs"
]

# ----------------------------
# Scraping function
# ----------------------------
def get_content_by_id(url: str, target_id: str):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    el = soup.find(id=target_id)
    if el is None:
        return soup.get_text(separator="\n")
    return el.get_text(separator="\n")

# ----------------------------
# Chunking functions
# ----------------------------
def split_into_sections(text: str, headings: List[str]) -> Dict[str, str]:
    headings_pattern = "|".join(headings) if headings else r"^$"
    split_pattern = r"(" + headings_pattern + r")\s*\n"
    test_pattern = r"^(" + headings_pattern + r")$"

    parts = re.split(split_pattern, text, flags=re.IGNORECASE)
    sections = {}
    current_heading = "Header/Intro"
    buffer = []
    for part in parts:
        clean = part.strip()
        if not clean:
            continue
        if re.match(test_pattern, clean, flags=re.IGNORECASE):
            if buffer:
                sections[current_heading] = "\n".join(buffer).strip()
                buffer = []
            current_heading = clean
        else:
            buffer.append(clean)
    if buffer:
        sections[current_heading] = "\n".join(buffer).strip()
    return sections

def sliding_window_preserve_lines(text: str, max_tokens: int = 800, overlap: int = 100) -> List[str]:
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = []
    word_count = 0
    for line in lines:
        line_words = len(line.split())
        if word_count + line_words > max_tokens and current_chunk:
            chunks.append("".join(current_chunk))
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

def chunk_judgment(text: str, headings, max_tokens: int = 800, overlap: int = 100) -> List[Dict]:
    sections = split_into_sections(text, headings)
    all_chunks = []
    for sec_name, sec_text in sections.items():
        if sec_name.lower() in ["legal context", "costs"]: continue
        windows = sliding_window_preserve_lines(sec_text, max_tokens=max_tokens, overlap=overlap)
        for i, chunk in enumerate(windows):
            all_chunks.append({
                "section": sec_name,
                "chunk_id": f"{sec_name}_{i+1}",
                "text": chunk
            })
    return all_chunks

# ----------------------------
# Main app
# ----------------------------
url = st.text_input("Enter judgment case URL")

if st.button("Extract & Chunk") and url:
    try:
        with st.spinner("Fetching content..."):
            content = get_content_by_id(url, page_id)

        st.subheader("Original Extracted Text (Preview)")
        st.text_area("Extracted content", content[:2000], height=200)

        chunks = chunk_judgment(content, headings, max_tokens=int(max_tokens), overlap=int(overlap))

        st.subheader(f"Generated {len(chunks)} Chunks")
        for c in chunks:
            with st.expander(f"Section: {c['section']} | Chunk: {c['chunk_id']}"):
                # st.write(c["text"])
                st.text(c["text"])

    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")
st.caption("This app scrapes the judgment text, splits into sections by regex headings, and chunks with sliding window.")
