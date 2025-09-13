import os
import google.generativeai as genai

model = None
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("Warning: GOOGLE_API_KEY environment variable not set. The generate endpoint will not work.")
else:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
    except Exception as e:
        print(f"Error configuring Google Gemini AI: {e}")
