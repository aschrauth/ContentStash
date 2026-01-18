import requests
from readability import Document
from markdownify import markdownify as md

# Fetch the article
url = "https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations"
response = requests.get(url)
html_content = response.text

# Extract main content with readability
doc = Document(html_content)
readable_html = doc.summary()

# Find and print HTML around "Problem:"
print("=" * 80)
print("HTML AROUND 'Problem:':")
print("=" * 80)
# Find the position of "Problem:" in the HTML
problem_index = readable_html.find("Problem:")
if problem_index != -1:
    # Print 500 characters before and 1500 after to capture context
    start = max(0, problem_index - 500)
    end = min(len(readable_html), problem_index + 1500)
    print(readable_html[start:end])
else:
    print("'Problem:' not found in HTML")

print("\n" + "=" * 80)
print("MARKDOWN CONVERSION AROUND 'Problem:':")
print("=" * 80)

# Convert to Markdown
markdown_content = md(readable_html, heading_style="ATX")

# Find and print Markdown around "Problem:"
problem_index_md = markdown_content.find("Problem:")
if problem_index_md != -1:
    # Print 500 characters before and 1500 after
    start = max(0, problem_index_md - 500)
    end = min(len(markdown_content), problem_index_md + 1500)
    print(markdown_content[start:end])
else:
    print("'Problem:' not found in Markdown")

print("\n" + "=" * 80)
print("FULL MARKDOWN (first 3000 chars):")
print("=" * 80)
print(markdown_content[:3000])