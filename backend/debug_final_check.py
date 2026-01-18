import requests
from readability import Document
from markdownify import markdownify as md

# Fetch the article
url = "https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations"
print(f"Fetching: {url}\n")

response = requests.get(url)
response.raise_for_status()

# Extract with readability
doc = Document(response.text)
html_content = doc.summary()

# Find the specific section around "Edge case"
search_text = "Edge case"
index = html_content.find(search_text)

if index == -1:
    print(f"Could not find '{search_text}' in the content")
    print("\nSearching for variations...")
    # Try case-insensitive
    index = html_content.lower().find(search_text.lower())
    if index == -1:
        print("Still not found. Printing first 2000 chars of content:")
        print(html_content[:2000])
else:
    print(f"Found '{search_text}' at index {index}\n")
    
    # Extract surrounding context (500 chars before and after)
    start = max(0, index - 500)
    end = min(len(html_content), index + 500)
    
    html_chunk = html_content[start:end]
    
    print("=" * 80)
    print("RAW HTML AROUND 'Edge case':")
    print("=" * 80)
    print(html_chunk)
    print("\n")
    
    # Look for list structure
    print("=" * 80)
    print("ANALYZING LIST STRUCTURE:")
    print("=" * 80)
    
    # Find the broader context - look for <ol> tags
    ol_start = html_content.rfind("<ol", 0, index)
    ol_end = html_content.find("</ol>", index)
    
    if ol_start != -1 and ol_end != -1:
        list_html = html_content[ol_start:ol_end + 5]
        print("Full <ol> containing 'Edge case':")
        print(list_html)
        print("\n")
    else:
        print("Could not find complete <ol> tag structure")
        print(f"ol_start: {ol_start}, ol_end: {ol_end}")
        print("\n")
    
    # Convert the chunk to markdown
    print("=" * 80)
    print("MARKDOWN CONVERSION OF CHUNK:")
    print("=" * 80)
    markdown_chunk = md(html_chunk)
    print(markdown_chunk)
    print("\n")
    
    # If we found the full list, convert that too
    if ol_start != -1 and ol_end != -1:
        print("=" * 80)
        print("MARKDOWN CONVERSION OF FULL LIST:")
        print("=" * 80)
        markdown_list = md(list_html)
        print(markdown_list)