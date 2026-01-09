import speech_recognition as sr

valid_swaras = ["sa", "ri", "ga", "ma", "pa", "da", "ni"]

recognizer = sr.Recognizer()
mic = sr.Microphone()

print("🎙️ Say swaras like 'sa ri ga ma...' (Press Ctrl+C to stop)\n")

try:
    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening...")
            audio = recognizer.listen(source)

        try:
            result = recognizer.recognize_google(audio).lower()
            print(f"You said: {result}")

            spoken_swaras = [word for word in result.split() if word in valid_swaras]

            if spoken_swaras:
                print("🎵 Detected Swaras:", " ".join(spoken_swaras))
            else:
                print("No valid swaras detected.")
        except sr.UnknownValueError:
            print("Didn't catch that, try again.")
        except sr.RequestError as e:
            print(f"API Error: {e}")
except KeyboardInterrupt:
    print("\n🛑 Stopped by user.")
