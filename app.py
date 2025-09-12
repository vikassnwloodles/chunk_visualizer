import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict
from chunking import chunk_judgment

st.set_page_config(page_title="Judgment Chunk Visualizer", layout="wide")
st.title("📑 Judgment Chunk Visualizer")

# ----------------------------
# Sidebar configuration
# ----------------------------
st.sidebar.header("Settings")

# page_id = st.sidebar.text_input("HTML element id", value="document_content")
max_tokens = st.sidebar.number_input("Max words per chunk", value=300, min_value=50, max_value=5000)
# overlap = st.sidebar.number_input("Overlap words", value=0, min_value=0, max_value=1000)
overlap = 0

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

def get_html_by_id(url: str, target_id: str):
    # Get the page content
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    if target_id:
        element = soup.find(id=target_id)
    else:
        element = soup

    # Convert element back to string
    html_str = str(element)

    # Normalize whitespace:
    # 1. Replace non-breaking space (\u00A0) with normal space
    # 2. (Optional) collapse multiple whitespace into a single space
    normalized_html = (
        html_str
        .replace("\u00A0", " ")   # nbsp → space
        .replace("\u200B", "")    # zero-width space → remove
    )

    return normalized_html

# ----------------------------
# Chunking functions
# ----------------------------


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

# def chunk_judgment(text: str, max_tokens: int = 800, overlap: int = 100) -> List[Dict]:
#     # sections = split_into_sections(text, headings)
#     sections = split_into_sections(html)
#     all_chunks = []
#     for sec_name, sec_text in sections.items():
#         if sec_name.lower() in ["legal context", "costs"]: continue
#         windows = sliding_window_preserve_lines(sec_text, max_tokens=max_tokens, overlap=overlap)
#         for i, chunk in enumerate(windows):
#             all_chunks.append({
#                 "section": sec_name,
#                 "chunk_id": f"{sec_name}_{i+1}",
#                 "text": chunk
#             })
#     return all_chunks

# ----------------------------
# Main app
# ----------------------------
url = st.text_input("Enter judgment case URL")

if st.button("Extract & Chunk") and url:
    try:
        with st.spinner("Fetching content..."):
            response = requests.get(url)

        html = response.content
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = soup.find_all("p")
        preview_text = []
        for p in paragraphs:
            preview_text.append(p.get_text().replace("\xa0", " ").strip())
        
        preview_text = "\n".join(preview_text)

        st.subheader("Original Extracted Text (Preview)")
        st.text_area("Extracted content", preview_text[:2000], height=200)

        chunks = chunk_judgment(html, max_tokens=int(max_tokens), overlap=int(overlap))

        st.subheader(f"Generated {len(chunks)} Chunks")
        for c in chunks:
            with st.expander(f"Section: {c['section']} | Chunk: {c['chunk_id']}"):
                # st.write(c["text"])
                st.text(c["text"])

    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")
st.caption("This app scrapes the judgment text, splits into sections by regex headings, and chunks with sliding window.")
