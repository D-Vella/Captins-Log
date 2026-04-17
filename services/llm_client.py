import json


def call_llm_api(prompt: str, system: str, format: str ="json") -> str:
    import requests

    # model is served on http://localhost:11434
    payload = {
        "model": "gemma4:e4b",
        "stream": False,
        "think": False, 
        "system": system,
        "prompt": prompt
            }
    
    if format == "json":
        payload["format"] = "json"

    api_response = requests.post('http://localhost:11434/api/generate',json=payload)

    import json
    returnMessages = api_response.text.splitlines()
    completeMessage = ''

    for idx, message in enumerate(returnMessages):
        returnMessage = json.loads(message)
        completeMessage += returnMessage['response']

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
    else:        print("✅ Markdown formatting completed successfully with length: " + str(len(markdown_response)) + " characters.")

    return markdown_response

def llm_question_generator(prompt: str) -> str:
    three_questions_prompt = """
        You will be given a diary entry. Based on the content of the diary entry, generate a list of 3 follow up questions that the user can ask themselves to reflect deeper on the content of the diary entry. The questions should be open ended and thought provoking. They should help them to gain deeper insights and understanding about themselves based on the content of the diary entry.
    """
    questions_response = call_llm_api(prompt=prompt, system=three_questions_prompt, format="json")
    if questions_response == None:
        raise ValueError("LLM API call for question generation failed. Aborting process.")
    else:
        print("✅ Question generation completed successfully with length: " + str(len(questions_response)) + " characters.")
    
    questions_response = json.loads(questions_response)
    question_text = ""
    for idx, question in enumerate(questions_response['follow_up_questions']):
        question_text += (f"Question {idx+1}: {question}\n")

    return question_text