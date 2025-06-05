from transformers import pipeline

# Use a small, free, open-source model for summarization
MODEL_NAME = "google/flan-t5-small"

_summarizer = None

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = pipeline("summarization", model=MODEL_NAME)
    return _summarizer

def summarize_text(text, max_length=100, min_length=20):
    """
    Summarize the given text using a free HuggingFace LLM.
    Args:
        text (str): The text to summarize.
        max_length (int): Maximum length of the summary.
        min_length (int): Minimum length of the summary.
    Returns:
        str: The summary text.
    """
    summarizer = get_summarizer()
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]['summary_text'] 