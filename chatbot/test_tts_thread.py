
import pyttsx3
import threading
import time
import queue

def tts_worker(q):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    print("TTS Worker started")
    while True:
        text = q.get()
        if text is None:
            break
        print(f"Speaking: {text}")
        engine.say(text)
        engine.runAndWait()
        q.task_done()
    print("TTS Worker finished")

def main():
    q = queue.Queue()
    t = threading.Thread(target=tts_worker, args=(q,))
    t.start()

    sentences = ["Hello there.", "This is a test.", "Of streaming TTS.", "While the main thread does other things."]
    
    for s in sentences:
        print(f"Main thread queuing: {s}")
        q.put(s)
        time.sleep(1.0) # Simulate LLM generation delay
    
    q.put(None)
    t.join()

if __name__ == "__main__":
    main()
