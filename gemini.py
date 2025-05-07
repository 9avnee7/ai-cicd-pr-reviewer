import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

def get_pr_fix_suggestions(pr_title, pr_description):
    prompt = f"""\
You are a code reviewer AI. A pull request has been flagged as 'buggy'. 
Here is the PR title and description:

Title: {pr_title}
Description: {pr_description}

Suggest specific improvements or bug fixes in concise points.
"""

    response = model.generate_content(prompt)
    return response.text


