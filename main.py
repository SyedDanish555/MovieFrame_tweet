import tweepy
import os
from dotenv import load_dotenv
import subprocess
import sys
import multiprocessing
import time

# Load environment variables from .env file if it exists
load_dotenv()

# Get API tokens from environment variables
bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
access_token = os.getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

# Verify all required tokens are present
if not all([bearer_token, consumer_key, consumer_secret, access_token, access_token_secret]):
    print("Error: Missing required Twitter API tokens in environment variables")
    sys.exit(1)

# Twitter API Authentication
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=False)  # Changed to False

# V2 Twitter API Authentication
client = tweepy.Client(
    bearer_token,
    consumer_key,
    consumer_secret,
    access_token,
    access_token_secret,
    wait_on_rate_limit=False,  # Changed to False
)

# Movie name
movie_name = "Pirates of the Caribbean: The Curse of the Black Pearl"

# Define the directory containing frames
frames_directory = "frames"

script_dir = os.path.dirname(os.path.abspath(__file__))
# renamed file that stores the last frame index the bot tweeted (matches filenames)
last_tweeted_file = os.path.join(script_dir, "last frame tweeted.txt")

# Load the last frame number from the file (frame index used in filenames)
try:
    with open(last_tweeted_file, "r") as f:
        content = f.read().strip()
        frame_number = int(content) if content else 1
except (FileNotFoundError, ValueError):
    frame_number = 1  # Start from 1 if the file doesn't exist or contains invalid data

print(f"Starting with frame number: {frame_number}")

# Function to find the next available frame
def find_next_available_frame(start_frame):
    current_frame = start_frame
    while True:
        frame_filename = f"frame_{current_frame:04d}.jpg"
        frame_path = os.path.join(frames_directory, frame_filename)
        if os.path.exists(frame_path):
            return current_frame, frame_path
        print(f"Frame {current_frame:04d} does not exist. Skipping...")
        current_frame += 1

# Function to delete the frame and commit the change
def delete_frame(frame_path):
    try:
        # Remove the file
        os.remove(frame_path)
        
        # Git commands to commit and push the change
        subprocess.run(["git", "config", "user.name", "GitHub Actions"])
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
        subprocess.run(["git", "add", frame_path])
        subprocess.run(["git", "commit", "-m", f"Delete frame {os.path.basename(frame_path)}"])
        subprocess.run(["git", "pull", "--rebase"])  # Pull and rebase before pushing
        subprocess.run(["git", "push"])
        
        print(f"Successfully deleted and committed: {frame_path}")
    except Exception as e:
        print(f"Error deleting frame: {e}")
 
def worker(start_frame):
    try:
        # Find next available frame (moved inside worker)
        frame_idx, frame_path = find_next_available_frame(start_frame)

        # Upload image to Twitter (this may block)
        media_id = api.media_upload(filename=frame_path).media_id_string

        total_frames = 7991
        text = f"{movie_name} - Frame {frame_idx:04d}/{total_frames:04d}"

        client.create_tweet(text=text, media_ids=[media_id])
        print(f"Tweeted: {text}")

        # Delete the frame (and attempt to commit)
        delete_frame(frame_path)

        # Save the last tweeted frame index
        try:
            with open(last_tweeted_file, "w") as f:
                f.write(str(frame_idx))
        except Exception as e:
            print(f"Warning: couldn't update last-tweeted file: {e}")

    except tweepy.errors.TooManyRequests:
        print("Rate limit exceeded. Exiting.")
    except tweepy.errors.TweepyException as e:
        print(f"Tweepy error while tweeting: {e}")
    except Exception as e:
        print(f"Unhandled error while tweeting: {e}")


# Run worker in a separate process and enforce 60 second timeout
if __name__ == "__main__":
    p = multiprocessing.Process(target=worker, args=(frame_number,))
    p.start()
    p.join(60)  # timeout after 60 seconds
    if p.is_alive():
        print("Tweeting operation exceeded 60 seconds, terminating worker.")
        p.terminate()
        p.join()
        sys.exit(1)
    else:
        print("Worker finished within 60 seconds.")
        sys.exit(1)