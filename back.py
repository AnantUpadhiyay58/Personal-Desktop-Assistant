import os
import datetime
import time
import subprocess
import pyautogui
import speech_recognition as sr
import requests
import webbrowser
import pywhatkit as kit
import noisereduce as nr
import numpy as np
from threading import Thread
from deep_translator import GoogleTranslator
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
from io import BytesIO
import pvporcupine
from pvrecorder import PvRecorder
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Global variables
weather_api_key = "343dfb812d196e284042489b46589867"
news_api_key = "c0dc9c67068045bb945b43009912d3ca"
ACCESS_KEY = "+TozAJkNJYIzoB5O7Xgz5K2NuYpJhEu62tN5xhsi4kx3E+sDf5kKeQ=="
KEYWORD_PATH = "Worcestershire_en_mac_v3_0_0.ppn"
GROQ_API_KEY = "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"
url = "https://api.groq.com/openai/v1/chat/completions"
stop_listener = False
translator = GoogleTranslator(source='auto', target='en')
is_taking_notes = False
current_note_content = ""
current_file_path = ""
NOTES_DIRECTORY = "/Users/anantupadhiyay/Documents/notes"

HINGLISH_MAPPING = {
    "kitna baje hai": "what time is it",
    "aaj ka mausam kaisa hai": "what's today's weather",
    "kya khabar hai": "what's the news",
    "video chalao": "play video",
    "video band karo": "stop video",
    "video fir se chalao": "resume video",
    "letter likho": "write letter",
    "notes likho": "take notes",
    "band karo": "stop",
}


def translate_hinglish(query):
    if query in HINGLISH_MAPPING:
        return HINGLISH_MAPPING[query]
    return translator.translate(query)


def mute_audio():
    if os.name == "nt":
        os.system("nircmd.exe mutesysvolume 1")
    elif os.name == "posix":
        os.system("osascript -e 'set volume output muted true'")


def unmute_audio():
    if os.name == "nt":
        os.system("nircmd.exe mutesysvolume 0")
    elif os.name == "posix":
        os.system("osascript -e 'set volume output muted false'")


def say(text):
    os.system(f"say '{text}'")


def wishme():
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        say("Good Morning! Sir")
    elif 12 <= hour < 18:
        say("Good Afternoon! Sir")
    else:
        say("Good Evening! Sir")
    say("Please tell me how I may help you.")


def takeCommand():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.pause_threshold = 0.8
        mute_audio()
        print("Listening for your command...")
        try:
            audio = recognizer.listen(source, timeout=5)
            audio_data = np.frombuffer(audio.frame_data, dtype=np.int16)
            reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=16000)
            query = recognizer.recognize_google(audio, language='hi-IN')
            print(f"User said: {query}")
            if any(word.isalpha() and word.isascii() for word in query.split()):
                print("Query contains English words. Skipping translation.")
                translated_query = query
            else:
                translated_query = translate_hinglish(query)
                print(f"Translated query (English): {translated_query}")
            query = translated_query
        except sr.UnknownValueError:
            print("Sorry, I could not understand the audio.")
            query = None
        except sr.RequestError:
            print("Could not request results from speech recognition service.")
            query = None
        except Exception as e:
            print(f"An error occurred: {e}")
            query = None
        finally:
            unmute_audio()
    return query


def get_time():
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    say(f"The current time is {current_time}.")
    return f"Assistant: The current time is {current_time}."


def groq(text, GROQ_API_KEY):
    print("Received info")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": "give me to the point short answer in simple text format, nothing else."},
            {"role": "user", "content": text}
        ]
    }
    print("Sending query")
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        print("Answer received")
        content = response_json["choices"][0]["message"]["content"]
        print(content)
        say(content)
        return content
    except requests.exceptions.RequestException as e:
        print(f"Error in Groq API request: {e}")
        say("Sorry, I encountered an error while processing your request.")
        return f"Assistant: Error processing request: {e}"


def generate_execute_and_show_output(prompt):
    try:
        print(f"DEBUG: Starting code generation for prompt: {prompt}")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        generation_prompt = f"""
        Generate complete, executable Python code based on this request: {prompt}
        Requirements:
        - do not write Here is the Python code for
        - Include all necessary imports
        - Add appropriate print statements to display results
        - Implement proper error handling with try-except blocks
        - Use clear variable names and basic comments
        - Avoid infinite loops by adding appropriate termination conditions
        - If input is needed, use default values instead of waiting for user input
        - Keep execution time under 60 seconds
        - Return only the raw Python code without markdown or explanations
        """
        print("DEBUG: Sending request to GroQ API")
        response = requests.post(url, headers=headers, json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": generation_prompt}],
            "temperature": 0.3,
            "max_tokens": 2000
        })
        if not response.ok:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            print(f"ERROR: {error_msg}")
            say("Error generating code")
            return error_msg
        response.raise_for_status()
        generated_code = response.json()["choices"][0]["message"]["content"]
        print(f"DEBUG: Code generated successfully:\n{generated_code}")
        if generated_code.startswith("```python"):
            generated_code = generated_code[9:-3]
        elif generated_code.startswith("```"):
            generated_code = generated_code[3:-3]
        os.makedirs(NOTES_DIRECTORY, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_code_{timestamp}.py"
        filepath = os.path.join(NOTES_DIRECTORY, filename)
        print(f"DEBUG: Saving code to {filepath}")
        with open(filepath, 'w') as f:
            f.write(generated_code)
        if not os.path.exists(filepath):
            error_msg = f"Failed to create file at {filepath}"
            print(f"ERROR: {error_msg}")
            say("Error saving generated code")
            return error_msg
        if "while True" in generated_code.lower() and "break" not in generated_code.lower():
            print("WARNING: Potential infinite loop detected")
            say("The generated code might contain an infinite loop. Would you like to execute it anyway? Say yes or no.")
            response = takeCommand()
            if not response or "no" in response.lower():
                return f"Generated code saved to: {filepath}\n\n=== CODE ===\n{generated_code}\n\nExecution skipped due to potential infinite loop"
        print("DEBUG: Attempting to execute the generated code")
        say("Executing the code now. Please wait.")
        process = subprocess.Popen(
            ['python', filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(timeout=60)
        return_code = process.returncode
        print(f"DEBUG: Code execution completed with return code: {return_code}")
        print(f"DEBUG: stdout: {stdout}")
        print(f"DEBUG: stderr: {stderr}")
        result = f"Generated code saved to: {filepath}\n\n"
        result += "=== CODE ===\n"
        result += generated_code + "\n\n"
        if stdout:
            result += "=== OUTPUT ===\n"
            result += stdout + "\n"
        else:
            result += "=== OUTPUT ===\n"
            result += "No output generated\n"
        if stderr or return_code != 0:
            result += "=== ERRORS ===\n"
            result += stderr + "\n" if stderr else f"Execution failed with return code {return_code}\n"
        if return_code == 0 and stdout:
            speak_output = stdout[:200]
            print(f"DEBUG: Speaking output: {speak_output}")
            say(speak_output)
        elif stderr:
            print("DEBUG: Speaking error notification")
            say("Code executed with errors: " + stderr[:100])
        else:
            print("DEBUG: Speaking no-output notification")
            say("Code executed but produced no output")
        return result
    except requests.exceptions.Timeout:
        error_msg = "API request timed out"
        print(f"ERROR: {error_msg}")
        say("Code generation timed out")
        return error_msg
    except subprocess.TimeoutExpired:
        error_msg = "Code execution timed out after 60 seconds"
        print(f"ERROR: {error_msg}")
        say("Code execution took too long")
        process.kill()
        stdout, stderr = process.communicate()
        result = f"Generated code saved to: {filepath}\n\n=== CODE ===\n{generated_code}\n\n=== ERROR ===\n{error_msg}"
        if stdout:
            result += f"\nPartial output: {stdout}"
        if stderr:
            result += f"\nError output: {stderr}"
        return result
    except Exception as e:
        error_msg = f"Error in code generation/execution: {str(e)}"
        print(f"ERROR: {error_msg}")
        say("Error processing code request")
        return error_msg


def get_weather(city):
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": weather_api_key, "units": "metric"}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        if weather_data.get("cod") != "404":
            temperature = weather_data.get("main", {}).get("temp", "N/A")
            weather = weather_data.get("weather", [{}])[0].get("description", "N/A")
            say(f"Temperature in {city} is {temperature:.2f} degrees Celsius. The weather is {weather}.")
            return f"Assistant: Temperature in {city} is {temperature:.2f}°C. Weather is {weather}."
        else:
            say("City not found.")
            return "Assistant: City not found."
    except requests.exceptions.RequestException as e:
        say(f"Error fetching weather information: {str(e)}")
        return f"Assistant: Error fetching weather information."


def get_news():
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={news_api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        news_data = response.json()
        if news_data.get("status") == "ok":
            articles = news_data.get("articles", [])
            if articles:
                say("Here are the top news headlines:")
                news_text = "Assistant: Top news headlines:\n"
                for i, article in enumerate(articles[:2]):
                    news_text += f"{i + 1}. {article.get('title', 'No title available')}\n"
                    say(f"Headline {i + 1}: {article.get('title', 'No title available')}")
                    time.sleep(1)
                return news_text
            else:
                say("No news articles found.")
                return "Assistant: No news articles found."
        else:
            say("Error fetching news.")
            return "Assistant: Error fetching news."
    except requests.exceptions.RequestException as e:
        say(f"Error fetching news: {str(e)}")
        return f"Assistant: Error fetching news."


def play_youtube_video(video_name):
    try:
        if not video_name:
            say("No video name provided. Please specify a video to play.")
            return "Assistant: No video name provided."
        say(f"Playing {video_name} on YouTube.")
        kit.playonyt(video_name)
        time.sleep(5)
        return f"Assistant: Playing {video_name} on YouTube."
    except Exception as e:
        say(f"Error playing video: {str(e)}")
        return f"Assistant: Error playing video. Please try again."


def pause_youtube_video():
    try:
        say("Pausing the video.")
        pyautogui.press('k')
        return "Assistant: Video paused."
    except Exception as e:
        say(f"Error pausing video: {str(e)}")
        return f"Assistant: Error pausing video."


def resume_youtube_video():
    try:
        say("Resuming the video.")
        pyautogui.press('k')
        return "Assistant: Video resumed."
    except Exception as e:
        say(f"Error resuming video: {str(e)}")
        return f"Assistant: Error resuming video."


def stop_assistant():
    global stop_listener
    stop_listener = True
    say("Stopping assistant. Goodbye!")
    return "Assistant: Stopping. Goodbye!"


def start_text_editor():
    global is_taking_notes, current_note_content, current_file_path
    try:
        os.makedirs(NOTES_DIRECTORY, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"note_{timestamp}.txt"
        current_file_path = os.path.join(NOTES_DIRECTORY, filename)
        with open(current_file_path, 'w') as f:
            f.write("")
        subprocess.Popen(['open', '-a', 'TextEdit', current_file_path])
        time.sleep(2)
        is_taking_notes = True
        current_note_content = ""
        say(f"I've opened a new document at {current_file_path}. Start dictating now. Say 'save file' when done.")
        return f"Assistant: New document opened at {current_file_path}. Speak and I'll type."
    except Exception as e:
        return f"Assistant: Error opening text editor: {str(e)}"


def add_to_note(text):
    global current_note_content
    try:
        text = text.replace("full stop", ".").replace("comma", ",")
        text = text.replace("new line", "\n").replace("next line", "\n")
        text = text.replace("question mark", "?").replace("exclamation mark", "!")
        current_note_content += text + " "
        pyautogui.write(text + " ", interval=0.05)
        return True
    except Exception as e:
        print(f"Error adding to note: {e}")
        return False


def save_text_file():
    global is_taking_notes, current_note_content, current_file_path
    try:
        if not current_note_content.strip():
            say("The document is empty. Save anyway?")
            response = takeCommand()
            if response and "no" in response.lower():
                is_taking_notes = False
                current_note_content = ""
                try:
                    os.remove(current_file_path)
                except:
                    pass
                say("Document discarded.")
                return "Assistant: Empty document discarded."
        pyautogui.hotkey('command', 's')
        time.sleep(1)
        try:
            save_btn = pyautogui.locateCenterOnScreen('save_button.png', confidence=0.7)
            if save_btn:
                pyautogui.click(save_btn)
            else:
                save_anyway_btn = pyautogui.locateCenterOnScreen('save_anyway_button.png', confidence=0.7)
                if save_anyway_btn:
                    pyautogui.click(save_anyway_btn)
        except:
            with open(current_file_path, 'w') as f:
                f.write(current_note_content)
        is_taking_notes = False
        current_note_content = ""
        say(f"Document saved successfully at {current_file_path}")
        return f"Assistant: Document saved at {current_file_path}"
    except Exception as e:
        is_taking_notes = False
        return f"Assistant: Error saving document: {str(e)}"


def write_letter():
    say("Which type of letter would you like to write? For example: leave application, job application, resignation letter, complaint letter, or business proposal.")
    letter_type = takeCommand()
    if not letter_type:
        say("Sorry, I didn't understand the letter type. Please try again.")
        return "Assistant: Could not determine letter type."
    say(f"You want to write a {letter_type}. Is that correct? Please say yes or no.")
    confirmation = takeCommand()
    if confirmation and "no" in confirmation.lower():
        say("Let's try again. Which type of letter would you like to write?")
        letter_type = takeCommand()
        if not letter_type:
            say("Sorry, I still didn't understand. Let's try this again later.")
            return "Assistant: Could not determine letter type."
    say(f"Generating a professional {letter_type} for you. Please wait while I prepare this...")
    prompt = f"""Generate a comprehensive professional {letter_type} with all necessary sections. 
    Include these parts:
    1. Sender's address (with placeholder)
    2. Date
    3. Recipient's address (with placeholder)
    4. Subject line
    5. Salutation
    6. Body (3-5 paragraphs)
    7. Closing
    8. Signature line
    Make it formal and business-appropriate. Use placeholders like [Your Name] where personal details should go."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        letter_content = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        say("Sorry, I encountered an error while generating the letter. Please try again later.")
        return f"Assistant: Error generating letter: {e}"
    os.makedirs(NOTES_DIRECTORY, exist_ok=True)
    clean_letter_type = ''.join(c for c in letter_type if c.isalnum() or c in (' ', '_')).rstrip()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{clean_letter_type.replace(' ', '_')}_{timestamp}.txt"
    filepath = os.path.join(NOTES_DIRECTORY, filename)
    try:
        with open(filepath, 'w') as f:
            f.write(letter_content)
        if os.name == 'nt':
            os.startfile(filepath)
        elif os.name == 'posix':
            subprocess.Popen(['open', '-a', 'TextEdit', filepath])
        say(f"I've successfully created your {letter_type} and saved it as {filename}. You can find it in your notes folder and edit it as needed.")
        return f"Assistant: Letter saved as {filepath}"
    except Exception as e:
        say("Sorry, I couldn't save the letter file. Please check your notes directory permissions.")
        return f"Assistant: Error saving letter: {e}"


def list_text_files():
    try:
        files = [f for f in os.listdir(NOTES_DIRECTORY) if f.endswith('.txt')]
        if not files:
            say("No text files found in your notes directory.")
            return "Assistant: No text files found."

        say("Here are the text files in your notes directory:")
        file_list = "Assistant: Available text files:\n"
        for i, f in enumerate(files[:5]):  # Limit to 5 files
            say(f"{i + 1}. {f}")
            file_list += f"{i + 1}. {f}\n"
        return file_list
    except Exception as e:
        say(f"Error listing files: {str(e)}")
        return f"Assistant: Error listing files: {str(e)}"


def convert_text_to_pdf():
    say("Which text file would you like to convert to PDF? Please say the file name without the extension.")
    filename = takeCommand()
    if not filename:
        say("Sorry, I didn't catch the file name. Please try again.")
        return "Assistant: File name not recognized."

    # Clean and format the filename
    filename = filename.lower().strip()
    filename = filename.replace("dot txt", "").replace(" ", "_")
    if not filename.endswith(".txt"):
        filename += ".txt"

    file_path = os.path.join(NOTES_DIRECTORY, filename)

    # Check if file exists
    if not os.path.exists(file_path):
        say(f"Sorry, the file {filename} was not found in the directory.")
        return f"Assistant: File {filename} not found in {NOTES_DIRECTORY}"

    try:
        # Read the text file content
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        # Create PDF filename
        pdf_filename = os.path.splitext(filename)[0] + ".pdf"
        pdf_path = os.path.join(NOTES_DIRECTORY, pdf_filename)

        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontName = "Helvetica"
        style.fontSize = 12
        style.leading = 14

        # Prepare content for PDF
        story = []
        paragraphs = text_content.split('\n')

        for para in paragraphs:
            if para.strip():  # Skip empty lines
                story.append(Paragraph(para, style))
                story.append(Paragraph("<br/><br/>", style))  # Add space between paragraphs

        # Build the PDF
        doc.build(story)

        # Open the PDF after creation
        if os.name == 'nt':
            os.startfile(pdf_path)
        elif os.name == 'posix':
            subprocess.Popen(['open', pdf_path])

        say(f"Successfully converted {filename} to PDF. It's saved as {pdf_filename} in your notes directory.")
        return f"Assistant: Converted {filename} to {pdf_filename} and saved in {NOTES_DIRECTORY}"

    except UnicodeDecodeError:
        say("Error: The file contains characters that couldn't be decoded. Please check the file encoding.")
        return "Assistant: Error - File contains undecodable characters."

    except Exception as e:
        error_msg = f"Error converting file to PDF: {str(e)}"
        say(error_msg)
        return f"Assistant: {error_msg}"


def process_command(query):
    print("Processing command")
    global is_taking_notes, current_note_content
    if not query:
        return "Assistant: No command recognized."
    query_lower = query.lower()
    if is_taking_notes:
        if any(word in query_lower for word in ["save file", "save document", "save this"]):
            return save_text_file()
        elif any(word in query_lower for word in ["cancel", "don't save", "discard"]):
            is_taking_notes = False
            current_note_content = ""
            try:
                os.remove(current_file_path)
            except:
                pass
            say("Document discarded.")
            return "Assistant: Document discarded."
        else:
            success = add_to_note(query)
            if success:
                return f"Assistant: Added to document: {query}"
            else:
                return "Assistant: Error adding to document."
    elif any(phrase in query_lower for phrase in ["list text files", "what text files", "available files"]):
        return list_text_files()
    elif any(phrase in query_lower for phrase in ["convert text to pdf", "text to pdf", "make pdf from text"]):
        return convert_text_to_pdf()
    elif any(phrase in query_lower for phrase in ["write letter", "create letter", "compose letter"]):
        return write_letter()
    elif any(word in query_lower for word in ["i want to write text", "open text editor", "start dictation"]):
        return start_text_editor()
    elif any(phrase in query_lower for phrase in ["generate code", "write code", "create code", "code for"]):
        say("What code would you like me to generate and execute? Please describe it clearly.")
        code_description = takeCommand()
        if code_description:
            return generate_execute_and_show_output(code_description)
        else:
            return "Assistant: I didn't get a clear description of the code to generate."
    elif any(word in query_lower for word in ["play video", "play on youtube", "search video"]):
        say("Which video would you like to play?")
        video_name = takeCommand()
        if video_name:
            return play_youtube_video(video_name)
        else:
            return "Assistant: Video name not recognized."
    elif any(word in query_lower for word in ["pause video", "pause the video"]):
        return pause_youtube_video()
    elif any(word in query_lower for word in ["resume video", "resume the video"]):
        return resume_youtube_video()
    elif any(word in query_lower for word in ["time", "current time", "what is the time"]):
        return get_time()
    elif any(word in query_lower for word in ["weather", "temperature", "how is the weather"]):
        say("Please tell me the city name.")
        city = takeCommand()
        if city:
            return get_weather(city)
        else:
            return "Assistant: City not recognized."
    elif any(word in query_lower for word in ["news", "headlines", "latest news"]):
        return get_news()
    elif any(word in query_lower for word in ["stop", "exit", "goodbye"]):
        return stop_assistant()
    else:
        print("Asking Groq")
        return groq(query, GROQ_API_KEY)


class VoiceAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Assistant")
        self.root.attributes("-fullscreen", True)
        self.mic_photo = self.load_image("https://cdn-icons-png.flaticon.com/128/25/25682.png", (50, 50))
        self.home_photo = self.load_image("https://cdn-icons-png.flaticon.com/128/25/25694.png", (50, 50))
        self.chat_photo = self.load_image("https://cdn-icons-png.flaticon.com/128/6396/6396259.png", (50, 50))
        self.center_image = self.load_image("https://i.pinimg.com/736x/20/ff/d7/20ffd75ad4339fe691d3fb6fffd9cdec.jpg",
                                            (500, 500))
        self.top_left_frame = tk.Frame(root)
        self.top_left_frame.place(x=10, y=10)
        self.chat_button = tk.Button(self.top_left_frame, image=self.chat_photo, command=self.show_chat_history,
                                     bg="lightyellow", fg="black")
        self.chat_button.grid(row=0, column=0, padx=5)
        self.home_button = tk.Button(self.top_left_frame, image=self.home_photo, command=self.go_home, bg="lightgreen",
                                     fg="black")
        self.home_button.grid(row=0, column=1, padx=5)
        self.chat_history = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20, state='disabled')
        self.chat_history.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        self.center_frame = tk.Frame(root)
        self.center_frame.pack(side=tk.TOP, pady=10)
        self.image_button = tk.Button(self.center_frame, image=self.center_image, command=self.go_home, bg="lightgreen",
                                      fg="black")
        self.image_button.pack()
        self.bottom_center_frame = tk.Frame(root)
        self.bottom_center_frame.pack(side=tk.BOTTOM, pady=20)
        self.mic_button = tk.Button(self.bottom_center_frame, image=self.mic_photo, command=self.start_listening,
                                    bg="lightblue", fg="black")
        self.mic_button.pack()
        self.update_chat_history("Assistant: Hello! How can I assist you today?")

    def load_image(self, url, size):
        try:
            response = requests.get(url)
            response.raise_for_status()
            image_data = BytesIO(response.content)
            image = Image.open(image_data)
            image = image.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def start_listening(self):
        self.update_chat_history("You: Listening...")
        wishme()
        Thread(target=self.hotword_listener).start()

    def hotword_listener(self):
        porcupine = pvporcupine.create(access_key=ACCESS_KEY, keyword_paths=[KEYWORD_PATH])
        recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
        recorder.start()
        print("Listening for the wake word 'assistant'...")
        try:
            while not stop_listener:
                pcm = recorder.read()
                if porcupine.process(pcm) >= 0:
                    say("How may I assist you?")
                    query = takeCommand()
                    if query:
                        if "exit" in query.lower():
                            stop_assistant()
                        else:
                            response = process_command(query)
                            if response:
                                self.update_chat_history(response)
        except Exception as e:
            print(f"Error in hotword listener: {e}")
        finally:
            recorder.stop()
            recorder.delete()
            porcupine.delete()

    def process_user_command(self):
        query = takeCommand()
        if query:
            self.update_chat_history(f"You: {query}")
            response = process_command(query)
            if response:
                self.update_chat_history(response)

    def go_home(self):
        self.update_chat_history("Assistant: Welcome back! How can I assist you?")

    def show_chat_history(self):
        self.chat_history.config(state='normal')
        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')

    def update_chat_history(self, message):
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, message + "\n")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)


if __name__ == "__main__":
    if not os.path.exists(NOTES_DIRECTORY):
        os.makedirs(NOTES_DIRECTORY)
    root = tk.Tk()
    app = VoiceAssistantApp(root)
    root.mainloop()
