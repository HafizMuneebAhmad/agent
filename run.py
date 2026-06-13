import uvicorn
import webbrowser
import threading
import time

def open_browser():
    # Wait for the server to spin up
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("Starting Nexus Learning Orchestrator local server...")
    
    # Run browser trigger in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run uvicorn server
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
    

