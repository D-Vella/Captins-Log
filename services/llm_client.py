import json

import httpx
import datetime
from services.config import OLLAMA_PRIMARY, OLLAMA_PRIMARY_MODEL, OLLAMA_FALLBACK, OLLAMA_FALLBACK_MODEL


def check_connection(endpoint_type: str) -> str:
    """
    Checks the connectivity to the specified endpoint type.
    :param endpoint_type: "primary" or "secondary"
    :return: "OK" if reachable, an error message otherwise
    """
    if endpoint_type == "primary":
        endpoint = OLLAMA_PRIMARY
    elif endpoint_type == "secondary":
        endpoint = OLLAMA_FALLBACK
    else:
        raise ValueError("Invalid endpoint type. Must be 'primary' or 'secondary'.")

    try:
        response = httpx.get(f"{endpoint}/api/version", timeout=2)
        response.raise_for_status()  # Raise an error for bad responses
        return "OK"
    except Exception as e:
        return f"Error: {e}"


def get_ollama_endpoint() -> tuple:
      """
        Returns the primary endpoint if reachable, otherwise returns the fallback endpoint.
      """
      try:
          httpx.get(f"{OLLAMA_PRIMARY}/api/version", timeout=2)
          print(f"Using LLM endpoint: {OLLAMA_PRIMARY}")
          return OLLAMA_PRIMARY, OLLAMA_PRIMARY_MODEL
      except Exception:
          print(f"Primary endpoint unreachable. Using fallback endpoint: {OLLAMA_FALLBACK}")
          return OLLAMA_FALLBACK, OLLAMA_FALLBACK_MODEL


def call_llm_api(prompt: str, system: str, format: str ="json") -> str:
    import requests
    start_time = datetime.datetime.now()
    LLM_ENDPOINT, LLM_MODEL = get_ollama_endpoint()

    payload = {
        "model": LLM_MODEL,
        "stream": False,
        "think": False, 
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    }

    if format == "json":
        payload["format"] = "json"

    api_response = requests.post(f'{LLM_ENDPOINT}/api/chat', json=payload, timeout=600)
    api_response.raise_for_status()

    import json
    returnMessages = api_response.text.splitlines()
    completeMessage = ''

    for idx, message in enumerate(returnMessages):
        returnMessage = json.loads(message)
        completeMessage += returnMessage.get('message', {}).get('content', '')

    end_time = datetime.datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    print(f"LLM API call completed in {elapsed_time:.2f} seconds with response length: {len(completeMessage)} characters.")
    return completeMessage

def llm_formatter(prompt: str) -> str:
    markdown_prompt = """
        You will be provided with a raw transcript of a diary like entry. Your job is to Convert the raw transcript into a neatly formatted markdown document. Use headings, bullet points, bold text, or any other formatting you think is appropriate to make the content easy to read and visually appealing.

        An entry may contain multiple topics or themes but should be organized coherently. Expect that some topics maybe visted multiple times in the same entry but in different places. Try and group related topics together. If you identify distinct topics, consider using headings to separate them. Use bullet points for lists or key takeaways. You can also use bold text to highlight important insights or reflections.

        Apply the following rules when processing the raw transcript:
        - Remove speech-to-text artefacts ("um", "uh", false starts).
        - Fix any punctuation, capitalisation and spacing issues.
        - Preserve the speaker's voice and meaning.
        - fix any grammatical errors that may have been introduced by the speech-to-text process.
        
        Ensure the final markdown document is well-structured and easy to read, while accurately reflecting the content of the original transcript.
    """
    markdown_response = call_llm_api(prompt=prompt, system=markdown_prompt, format="markdown")
    if markdown_response == None:
        raise ValueError("LLM API call for markdown formatting failed. Aborting process.")

    return markdown_response

def llm_question_generator(prompt: str) -> str:
    three_questions_prompt = """
                You will be given a diary entry. Based on the content of the diary entry, generate a list of 3 follow up questions that the user can ask themselves to reflect deeper on the content of the diary entry. The questions should be open ended and thought provoking. They should help them to gain deeper insights and understanding about themselves based on the content of the diary entry.
        
        Your response will be a JSON object with a single key "follow_up_questions" which is a list of the three questions you have generated. Do not include any other text in your response.
    """
    questions_response = call_llm_api(prompt=prompt, system=three_questions_prompt, format="json")
    if questions_response == None:
        raise ValueError("LLM API call for question generation failed. Aborting process.")
    
    if questions_response.startswith('```'):
        questions_response = questions_response.split('\n', 1)[1]
        questions_response = questions_response.rsplit('```', 1)[0].strip()

    try:
        questions_response = json.loads(questions_response)
        question_text = ""
        for idx, question in enumerate(questions_response['follow_up_questions']):
            question_text += (f"\n\n### Question {idx+1}:\n\n{question}\n\n")
    except Exception as e:
        print("Issue with LLM response. Printing raw response.")
        print(f"\n{repr(questions_response)}")
        raise ValueError(f"Failed to parse question generation response: {e}")

    return question_text

def weekly_review(prompt: str) ->str:
    weekly_review_prompt = """
        You will be given a week's worth of diary entries. Based on the content of these entries, generate a weekly review that coverts the following topics:
            * Summarise what was worked on across the week
            * Identify recurring themes or blockers
            * List any outstanding actions mentioned but not resolved
            * Note what went well vs. what didn't
        The goal of this review is to help the user reflect on their week, identify areas for improvement, and celebrate their wins. 
    """
    weekly_review_response = call_llm_api(prompt=prompt, system=weekly_review_prompt, format="markdown")
    if weekly_review_response == None:
        raise ValueError("LLM API call for weekly review generation failed. Aborting process.")

    return weekly_review_response

def transcription_cleanup(prompt: str, mode_choice: str = "Transcription Cleanup") -> str:
    cleanup_prompt = """
        You will be given a raw transcript of a diary like entry. Your job is to clean up the transcript by removing any speech-to-text artefacts ("um", "uh", false starts), fixing any punctuation, capitalisation and spacing issues, while preserving the speaker's voice and meaning. The cleaned up transcript should be easy to read and accurately reflect the content of the original transcript.
    """
    note_taking_prompt = """
    You will be given a raw transcript of a dictation from an individual who is doing analysis or investigations into a given topic. Your job is to clean up any speech to text artefacts, fix punctuation, capitalization, paragraphing and spacing issues, while preserving the speaker's voice and meaning. Additionally, you are to assist with the organization of the information to help present a useful entry that can be read back at a later date. The goal here is to provide understanding and clarity of the topic at hand to someone who has been divorced from the topic in question by a matter of days. Feel free to add some additional information where it can be ascertained from the original transcription to improve clarity of the outputted text.
"""

    prompts = {
        "Transcription Cleanup": cleanup_prompt,
        "Note Taking": note_taking_prompt,
    }
    if mode_choice not in prompts:
        raise ValueError(f"Unknown processing mode: {mode_choice}")
    system_prompt = prompts[mode_choice]

    cleanup_response = call_llm_api(prompt=prompt, system=system_prompt, format="markdown")
    if cleanup_response == None:
        raise ValueError("LLM API call for transcription cleanup failed. Aborting process.")
    
    return cleanup_response