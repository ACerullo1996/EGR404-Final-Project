import openai
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog
import time
import os

openai.api_key = os.getenv('OPENAI_API_KEY')

SYSTEM_PROMPT = """
You are a scientific assistant trained in neuroscience.
Summarize the contents of this PDF, focusing on EEG/fNIRS methods, brain regions, tasks used, results, and conclusions.
Structure your response into: Purpose, Methods, Results, and Conclusion.

Identify Metadata such as:
Paper Name
Authors
Year of Publication
Journal
Impact Factor
Keywords

Identify information such as:

Experimental Design:
- Tasks/conditions
- Modalities (e.g., EEG, fNIRS)
- Expected brain regions of interest
- Sample size suggestion
- Trial structure and durations
- Statistical comparisons

Summary of the results and conclusions.
What future works do the authors mention?
"""

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)

def summarize_text(text):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        temperature=0,
        max_tokens=2048
    )
    return response.choices[0].message.content.strip()

def select_pdfs():
    root = tk.Tk()
    root.withdraw()
    files = tk.filedialog.askopenfilenames(
        title="Select multiple PDF files",
        filetypes=[("PDF files", "*.pdf")]
    )
    return list(files)

def merge_summaries(output_file="AllSummaries.txt", output_dir="."):
    summary_files = [f for f in os.listdir(output_dir) if f.endswith("_summary.txt")]
    summary_files.sort()

    merged_path = os.path.join(output_dir, output_file)
    with open(merged_path, "w", encoding="utf-8") as outfile:
        for file in summary_files:
            file_path = os.path.join(output_dir, file)
            title = os.path.splitext(file)[0]
            with open(file_path, "r", encoding="utf-8") as infile:
                outfile.write(f"\n\n===== Summary for: {title} =====\n\n")
                outfile.write(infile.read())
                outfile.write("\n" + "=" * 50 + "\n")

    print(f"\nMerging Summaries: {merged_path}")

def summarize_combined_summaries(file_path, output_dir="."):
    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    print("Summarizing AllSummaries.txt ...")

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": """
            You are a research assistant summarizing findings across multiple EEG/fNIRS studies.
            Identify information such as:
            Experimental Design:
            - Tasks/conditions
            - Modalities (e.g., EEG, fNIRS)
            - Expected brain regions of interest
            - Sample size suggestion
            - Trial structure and durations
            - Statistical comparisons
            Summary of the results and conclusions.
            What future works do the authors mention?
            """},
            {"role": "user", "content": f"Summarize the following multi-paper review:\n\n{full_text}"},
        ],
        temperature=0,
        max_tokens=2048
    )

    meta_summary = response.choices[0].message.content.strip()
    output_path = os.path.join(output_dir, "AllSummaries_MetaSummary.txt")

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(meta_summary)

    print(f"Saving: {output_path}\n")

def generate_hypothesis_and_protocol(meta_path, full_path, output_dir="."):
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_summary = f.read()

    with open(full_path, "r", encoding="utf-8") as f:
        all_summary = f.read()

    print("Generating experimental hypothesis and protocol from summaries...")

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a cognitive neuroscience researcher specializing in experimental design."},
            {"role": "user", "content": f"""
Based on the following summaries, generate a clear and testable experimental hypothesis and a proposed protocol.

Summarized Findings Across Papers:
{meta_summary}

Detailed Study Summaries:
{all_summary}

Your response should include:

1. Hypothesis (1-2 sentences)
2. Justification (linking summary themes)
3. Experimental Design:
    - Tasks/conditions
    - Modalities (e.g., EEG, fNIRS)
    - Expected brain regions of interest
    - Sample size suggestion
    - Trial structure and durations
    - Statistical comparisons

Be precise and format your response clearly.
"""}
        ],
        temperature=0,
        max_tokens=2048
    )

    output = response.choices[0].message.content.strip()
    output_path = os.path.join(output_dir, "Proposed_Hypothesis_And_Protocol.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Saving: {output_path}\n")

def main():
    pdf_paths = select_pdfs()
    if not pdf_paths:
        print("No files selected.")
        return

    output_dir = os.path.dirname(pdf_paths[0])

    for path in pdf_paths:
        filename = os.path.splitext(os.path.basename(path))[0]
        summary_file = os.path.join(output_dir, f"{filename}_summary.txt")

        if os.path.exists(summary_file):
            print(f"Skipping {filename}, summary already exists.")
            continue

        print(f"\nProcessing: {filename}")
        text = extract_text(path)

        try:
            summary = summarize_text(text)
        except openai.error.RateLimitError:
            print("Token Limit Hit. Waiting 60 seconds...")
            time.sleep(60)
            summary = summarize_text(text)

        time.sleep(1)

        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)

        print(f"Saving: {summary_file}")

    all_summaries_path = os.path.join(output_dir, "AllSummaries.txt")
    merge_summaries(output_file="AllSummaries.txt", output_dir=output_dir)
    summarize_combined_summaries(file_path=all_summaries_path, output_dir=output_dir)

    meta_summary_path = os.path.join(output_dir, "AllSummaries_MetaSummary.txt")
    generate_hypothesis_and_protocol(
        meta_path=meta_summary_path,
        full_path=all_summaries_path,
        output_dir=output_dir
    )

if __name__ == "__main__":
    main()
