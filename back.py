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

weather_api_key = "343dfb812d196e284042489b46589867"
news_api_key = "c0dc9c67068045bb945b43009912d3ca"
ACCESS_KEY = "+TozAJkNJYIzoB5O7Xgz5K2NuYpJhEu62tN5xhsi4kx3E+sDf5kKeQ=="
KEYWORD_PATH = "Worcestershire_en_mac_v3_0_0.ppn"
GROQ_API_KEY = "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"
url = "https://api.groq.com/openai/v1/chat/completions"
stop_listener = False
translator = GoogleTranslator(source='auto', target='en')  #
HINGLISH_MAPPING = {
    # Weather-related queries
    "वेदर क्या हो रहा है": "what is the weather",
    "मौसम कैसा है": "what is the weather",
    "तापमान बताओ": "what is the temperature",
    "आज का मौसम कैसा है": "what is the weather today",
    "बारिश हो रही है क्या": "is it raining",
    "हवा कैसी चल रही है": "how is the wind",
    "आज गर्मी कितनी है": "how hot is it today",
    "ठंड कितनी है": "how cold is it",
    "आज का तापमान क्या है": "what is today's temperature",
    "मौसम का हाल बताओ": "tell me the weather update",

    # Time-related queries
    "समय क्या है": "what is the time",
    "क्या टाइम हुआ है": "what is the time",
    "अभी टाइम क्या हो रहा है": "what is the time now",
    "वक़्त क्या हुआ है": "what is the time",
    "कितने बजे हैं": "what is the time",
    "टाइम बताओ": "tell me the time",
    "अभी कितना समय हुआ है": "what is the time now",
    "समय का पता करो": "check the time",
    "क्या समय हुआ है": "what is the time",
    "वक़्त बताओ": "tell me the time",

    # News-related queries
    "समाचार सुनाओ": "tell me the news",
    "आज की खबर": "today's news",
    "ताजा खबर क्या है": "what is the latest news",
    "दुनिया की खबर बताओ": "tell me world news",
    "आज के हेडलाइन्स क्या हैं": "what are today's headlines",
    "न्यूज़ अपडेट दो": "give me news update",
    "ताजा समाचार बताओ": "tell me the latest news",
    "आज क्या चल रहा है": "what is happening today",
    "खबरें सुनाओ": "tell me the news",
    "देश की खबर बताओ": "tell me national news",

    # YouTube-related queries
    "यूट्यूब पर वीडियो चलाओ": "play video on youtube",
    "वीडियो चलाओ": "play video",
    "यूट्यूब वीडियो": "play video on youtube",
    "मुझे यूट्यूब की वीडियो प्ले करके दे दो": "play video on youtube",
    "यूट्यूब वीडियो चलाओ": "play video on youtube",
    "यूट्यूब पर वीडियो प्ले कर दो": "play video on youtube",
    "वीडियो को पॉज करो": "pause video",
    "वीडियो रोको": "pause video",
    "वीडियो फिर से चलाओ": "resume video",
    "वीडियो जारी रखो": "resume video",
    "यूट्यूब पर गाना चलाओ": "play song on youtube",
    "गाना सुनाओ": "play song",
    "म्यूजिक चलाओ": "play music",
    "यूट्यूब पर मूवी चलाओ": "play movie on youtube",
    "मूवी चलाओ": "play movie",
    "वीडियो बंद करो": "stop video",
    "यूट्यूब बंद करो": "stop youtube",
    "वीडियो आगे बढ़ाओ": "skip video",
    "वीडियो पीछे करो": "rewind video",
    "यूट्यूब पर सर्च करो": "search on youtube",

    # General commands
    "बंद करो": "stop",
    "समाप्त करो": "stop",
    "अलविदा": "goodbye",
    "रुको": "wait",
    "शुरू करो": "start",
    "मदद करो": "help",
    "क्या कर रहे हो": "what are you doing",
    "तुम कौन हो": "who are you",
    "तुम्हारा नाम क्या है": "what is your name",
    "तुम क्या कर सकते हो": "what can you do",
}


def translate_hinglish(query):
    if query in HINGLISH_MAPPING:
        return HINGLISH_MAPPING[query]
    return translator.translate(query)


# Audio Functions
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
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
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

        # Use pywhatkit to directly play the video
        kit.playonyt(video_name)
        time.sleep(5)  # Wait for YouTube to load
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


# Command Processor
def process_command(query):
    print("Processing command")
    if not query:
        return "Assistant: No command recognized."

    query_lower = query.lower()

    # Play YouTube Video
    if any(word in query_lower for word in [
        "play video", "play a video", "play on youtube", "search video", "youtube video",
        "turn on the video on youtube", "anky video ran on youtube", "play video on youtube",
        "play song on youtube", "play music", "play movie on youtube", "play movie",
        "stop video", "stop youtube", "skip video", "rewind video", "search on youtube"
    ]):
        say("Which video would you like to play?")
        video_name = takeCommand()
        if video_name:
            return play_youtube_video(video_name)
        else:
            return "Assistant: Video name not recognized."


    elif any(word in query_lower for word in [
        "pause video", "pause the video", "pause youtube", "pause playback", "pose the video"
    ]):
        return pause_youtube_video()


    elif any(word in query_lower for word in [
        "resume video", "resume the video", "resume youtube", "continue video", "continue playback"
    ]):
        return resume_youtube_video()


    elif any(word in query_lower for word in
             ["time", "current time", "what is the time", "tell me the time", "time now"]):
        return get_time()

    elif any(word in query_lower for word in
             ["weather", "temperature", "how is the weather", "what's the weather", "weather update"]):
        say("Please tell me the city name.")
        city = takeCommand()
        if city:
            return get_weather(city)
        else:
            return "Assistant: City not recognized."

    elif any(word in query_lower for word in ["news", "headlines", "latest news", "today's news", "news update"]):
        return get_news()

    elif any(word in query_lower for word in ["stop", "exit", "goodbye", "close", "shut down", "terminate"]):
        return stop_assistant()

    else:
        print("Asking Groq")
        return groq(query, GROQ_API_KEY)


KEYWORD_PATH = "/Volumes/ANANT/My Projects/Projects/Personal projects/PERSONAL DESKTOP ASSISTANT/Personal Assistant/backend/Worcestershire_en_mac_v3_0_0.ppn"  # Relative path

def hotword_listener():
    try:
        porcupine = pvporcupine.create(access_key=ACCESS_KEY, keyword_paths=[KEYWORD_PATH])
        recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
        recorder.start()
        print("Listening for the wake word 'assistant'...")

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
                            print(response)
    except Exception as e:
        print(f"Error in hotword listener: {e}")
    finally:
        recorder.stop()
        recorder.delete()
        porcupine.delete()

class VoiceAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Assistant")
        self.root.attributes("-fullscreen", True)

        # Load images from URLs
        self.mic_photo = self.load_image("https://cdn-icons-png.flaticon.com/128/25/25682.png",
                                         (50, 50))
        self.home_photo = self.load_image("https://cdn-icons-png.flaticon.com/128/25/25694.png",
                                          (50, 50))
        self.chat_photo = self.load_image("https://cdn-icons-png.flaticon.com/128/6396/6396259.png",
                                          (50, 50))
        self.center_image = self.load_image("https://i.pinimg.com/736x/20/ff/d7/20ffd75ad4339fe691d3fb6fffd9cdec.jpg",
                                            (500, 500))


        self.top_left_frame = tk.Frame(root)
        self.top_left_frame.place(x=10, y=10)

        # Chat Button
        self.chat_button = tk.Button(self.top_left_frame, image=self.chat_photo, command=self.show_chat_history,
                                     bg="lightyellow", fg="black")
        self.chat_button.grid(row=0, column=0, padx=5)

        # Home Button
        self.home_button = tk.Button(self.top_left_frame, image=self.home_photo, command=self.go_home, bg="lightgreen",
                                     fg="black")
        self.home_button.grid(row=0, column=1, padx=5)

        # Chat history
        self.chat_history = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=20, state='disabled')
        self.chat_history.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Center frame for the image button
        self.center_frame = tk.Frame(root)
        self.center_frame.pack(side=tk.TOP, pady=10)

        # Image Button
        self.image_button = tk.Button(self.center_frame, image=self.center_image, command=self.go_home, bg="lightgreen",
                                      fg="black")
        self.image_button.pack()

        # Bottom center frame for Mic button
        self.bottom_center_frame = tk.Frame(root)
        self.bottom_center_frame.pack(side=tk.BOTTOM, pady=20)

        # Mic Button with Image
        self.mic_button = tk.Button(self.bottom_center_frame, image=self.mic_photo, command=self.start_listening,
                                    bg="lightblue", fg="black")
        self.mic_button.pack()

        # Initialize chat history
        self.update_chat_history("Assistant: Hello! How can I assist you today?")

    def load_image(self, url, size):
        """Load image from a URL and resize it."""
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
    root = tk.Tk()
    app = VoiceAssistantApp(root)
    root.mainloop()