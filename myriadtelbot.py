import json
import requests
import os
import re
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
callback_url = "https://app.myriad.social/login"
from datetime import datetime
from bs4 import BeautifulSoup

EMAIL, MAGIC_LINK, TOKEN = range(3)
# Base URL for the Myriad API
base_url = "https://api.myriad.social"

import urllib.parse
import re
import json
import html
import re

def parse_post(post):
    title = post.get('title', '')  # Default to an empty string if no title is found
    url = post.get('url', '')  # Default to an empty string if no url is found

    text = post.get('text', '')  # Get the text content
    # Handle nested complex JSON or HTML in the text
    parsed_text = parse_content(text)  # Using the parse_content function defined earlier

    result = ''
    if title:  # Check if there is a title
        result += f"Title: {title}\n"
    if url:  # Check if there is a URL
        result += f"URL: {url}\n"
    if parsed_text:  # Check if there is text
        result += f"Text: {parsed_text}\n"
    return result.strip()  # Remove any trailing newlines


def parse_content(content):
    parsed_content = ""
    images = []
    embed_links = []

    # Check if content might be HTML
    if '<' in content and '>' in content:
        # If the content is HTML, remove the tags and any script/style content
        soup = BeautifulSoup(content, features="html.parser")

        # Extract image URLs
        for img in soup.find_all('img', src=True):
            images.append(img['src'])

        # Extract URLs from iframe
        for iframe in soup.find_all('iframe', src=True):
            url = iframe['src']
            embed_links.append(url)

        # remove all javascript, stylesheet code, and img tags
        for tag in soup(["script", "style", "img", "iframe"]):
            tag.extract()

        parsed_content = soup.get_text(separator="\n")
        parsed_content = parsed_content.replace('&nbsp;', ' ')

    elif content.startswith('{') and content.endswith('}') or content.startswith('[') and content.endswith(']'):
        # If the content is JSON, extract the text
        try:
            json_content = json.loads(content)
        except json.JSONDecodeError:
            return content
        if isinstance(json_content, list):
            for item in json_content:
                if 'type' in item and item['type'] == 'p' and 'children' in item:
                    for child in item['children']:
                        if 'text' in child:
                            parsed_content += child['text'] + '\n'
    else:
        # If the content is just text, use it as is
        parsed_content = content

    parsed_content = parsed_content.strip()  # remove trailing newline if exists

    # append image and embed links at the end
    for img in images:
        parsed_content += "\n" + img
    for link in embed_links:
        parsed_content += "\n" + link

    return parsed_content

def parse_dict(json_dict):
    parsed_content = ""
    # If we have a title or url, add those
    for key, value in json_dict.items():
        if key == 'title':
            parsed_content += "Title: " + value + '\n'
        elif key == 'url':
            parsed_content += "URL: " + value + '\n'
        elif isinstance(value, dict):
            # If the value is a dictionary, recursively parse it
            parsed_content += parse_dict(value)
    return parsed_content


def embed(update: Update, context: CallbackContext, message: str):
    url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_regex, message)
    if urls:
        url = urls[0]
        caption = message.replace("embed", "").replace(url, "").strip()
        if 'youtube.com' in url:
            video_html = embed_youtube(url)
        elif 'twitch.tv' in url:
            video_html = embed_twitch(url)
        else:
            video_html = "The URL you've entered is neither a YouTube nor Twitch URL."
            update.message.reply_text(video_html)
            return TOKEN

        # Create the text_blocks list
        text_blocks = [caption, video_html]
        # Call the create_myriad_post function
        title = "Embedded Video"
        create_myriad_post(update, context, title, text_blocks)

    else:
        video_html = "There was no URL detected in your message."
        update.message.reply_text(video_html)
        return TOKEN


def embed_youtube(url: str) -> str:
    url = url.replace('watch?v=', 'embed/')
    video_html = f'<iframe width="100%" height="315" src="{url}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>'
    return video_html

def embed_twitch(url: str) -> str:
    twitch_user = url.split('twitch.tv/')[1]
    video_html = f'<iframe src="https://player.twitch.tv/?channel={twitch_user}&parent=app.myriad.social" frameborder="0" allowfullscreen="true" scrolling="no" height="378" width="100%"></iframe>'
    return video_html

def import_post(update: Update, context: CallbackContext, post_url, importer="twitter", selected_timeline_ids=None):
    print("Entering import_post()")
    
    base_url = "https://api.myriad.social"
    api_endpoint = f"{base_url}/user/posts/import"
    
    username = update.message.from_user.username
    with open("emails.json", "r") as file:
        data = json.load(file)
    at = data[username]['accesstoken']
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + at,
    }
    
    data = {
        "url": post_url,
        "importer": importer,
        "selectedTimelineIds": selected_timeline_ids if selected_timeline_ids else [],
    }
    
    response = requests.post(api_endpoint, headers=headers, json=data)
    print(response)
    if response.status_code == 200:
        update.message.reply_text("Post successfully imported into Myriad.")
        print("Post successfully imported into Myriad.")
    else:
        update.message.reply_text(f"Error importing post: {response.status_code}")
        print(f"Error importing post: {response.status_code}")
    return TOKEN


def create_myriad_post(update: Update, context: CallbackContext, title, text_blocks, platform='myriad', visibility='public') -> int:
    print("Entering create_myriad_post()")
    
    username = update.message.from_user.username
    with open("emails.json", "r") as file:
        data = json.load(file)
    at = data[username]['accesstoken']
    myriad_username = data[username]['myriad_username']
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + at,
    }

    api_endpoint = f"{base_url}/user/posts"

    response = requests.get(f"{base_url}/users/{myriad_username}", headers=headers)
    if response.status_code == 200:
        user_data = json.loads(response.text)
        created_by = user_data.get("id")
        print(f"User ID: {created_by}")
    else:
        update.message.reply_text("Error retrieving user ID.")
        print(f"Error retrieving user ID: {response.status_code}")
        return TOKEN

    now = datetime.now()
    createdAt = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    text = json.dumps([
        {"type": "p", "children": [{"text": block}]} for block in text_blocks
    ])

    post_data = {
        "rawText": '\n'.join(text_blocks),
        "text": '\n'.join(text_blocks),  # Use the same value as 'rawText'
        "status": "published",
        "selectedTimelineIds": []
    }


    response = requests.post(api_endpoint, headers=headers, json=post_data)
    if response.status_code == 200:
        update.message.reply_text("Post created successfully!")
        print("Post created successfully!")
    else:
        update.message.reply_text(f"Error creating post: {response.status_code}")
        print(f"Error creating post: {response.status_code}")

    return TOKEN

def post(update: Update, context: CallbackContext) -> int:
    print("Entering post()")
    
    command, *content = update.message.text.split(' ', 1)
    command = command.lower()
    
    if command == "post":
        if content:  # Check if there is any content
            content = content[0].split('\n\n')
            content = [c.strip() for c in content if c.strip()]  # Remove whitespace-only strings
            if not content:  # Check if the content is empty
                update.message.reply_text("Cannot create an empty post.")
                return TOKEN
            print(f"Post content: {content}")
            create_myriad_post(update, context, "My Post Title", content)
        else:
            update.message.reply_text("Cannot create an empty post.")
            return TOKEN
        
        
    elif command == "import":
        if content:  # Check if there is any content
            url = content[0].strip()
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc in ['twitter.com', 'www.twitter.com', 'reddit.com', 'www.reddit.com', 'x.com', 'www.x.com']:
                import_post(update, context, url)
            else:
                update.message.reply_text("Invalid URL. Only URLs from twitter.com, reddit.com, and x.com are supported.")
                return TOKEN
        else:
            update.message.reply_text("No URL provided to import.")
            return TOKEN
    elif command == "embed":
        if content:
            embed(update, context, content[0])
        else:
            update.message.reply_text("No URL provided to embed.")
            return TOKEN    
    
    elif command == "view":
        if content:  # Check if there is any content
            limit = content[0].strip()
            if limit.isdigit():
                limit = int(limit)
                if limit <= 0:
                    update.message.reply_text("The number of posts to view must be greater than zero.")
                    return TOKEN
            else:
                update.message.reply_text("Invalid number of posts to view.")
                return TOKEN
        else:
            limit = 10  # Default number of posts to view

        # Get the posts from the API
        response = requests.get(f'https://api.myriad.social//user/posts?pageLimit={limit}')

        if response.status_code != 200:
            update.message.reply_text(f"Error: Received status code {response.status_code} from Myriad API.")
            return TOKEN

        posts = json.loads(response.text)['data']
        message = ''
        for i, post in enumerate(posts, start=1):
            user = post['user']['name']
            text = parse_post(post)  # Parse the post here  # Parse the content here
            message = f"{i}. {user}: {text}\n\n"

            # Send the posts to the user
            update.message.reply_text(message.strip())

    return TOKEN
        





def is_user_logged_in(username):
    # Load the JSON data from the file
    with open("emails.json", "r") as file:
        data = json.load(file)
    # Check if the user is in the data and if they have an access token
    if username in data and 'accesstoken' in data[username]:
        return True
    else:
        return False

# Message handler for MAGIC_LINK state
def magic_link(update: Update, context: CallbackContext) -> int:
    magic_link = update.message.text
    username = update.message.from_user.username

    with open("emails.json", "r") as file:
        data = json.load(file)
    data[username]['magic_link'] = magic_link
    with open("emails.json", "w") as file:
        json.dump(data, file)

    update.message.reply_text("Magic link received! Now we'll try to authenticate you.")
    
    auth=magic_link.replace(callback_url+"?token=","")
 # ...
    response = authenticate(auth)
    if response is not None:
        # Retrieve the access token and username
        accesstoken = response['accessToken']
        myriad_username = response['username']
        with open("emails.json", "r") as file:
            data = json.load(file)
        if username in data:
            data[username]['accesstoken'] = accesstoken
            data[username]['myriad_username'] = myriad_username  # Save the Myriad username
        with open("emails.json", "w") as file:
            json.dump(data, file)
        update.message.reply_text("You are now logged in!")
        return ConversationHandler.END
    else:
        update.message.reply_text("Authentication failed. Please try again.")
        return MAGIC_LINK




# Function to send a magic link to the user's email address
def send_magic_link(email, username, update: Update, context: CallbackContext) -> int:
    # Myriad API endpoint for sending a magic link
    api_endpoint = f"{base_url}/authentication/otp/email"

    # Prepare the payload with the email address and callback URL
    payload = {
        "email": email,
        "callbackURL": callback_url
    }

    # Send a POST request to the Myriad API to send a magic link
    response = requests.post(api_endpoint, json=payload)

    # Check if the request was successful
    if response.status_code == 200:
        update.message.reply_text(f"Magic link successfully sent to {email}.")
        update.message.reply_text("Please check your email, then copy and paste the magic link here.")
        return MAGIC_LINK
    else:
        update.message.reply_text(f"Error sending magic link: {response.status_code}")
        update.message.reply_text(response.text)
        return EMAIL


        
def authenticate(token):
    api_endpoint = f"{base_url}/authentication/login/otp"
    payload = {"token": token}
    response = requests.post(api_endpoint, json=payload)
    
    if response.status_code == 200:
        response_json = response.json()
        print(response_json)
        if 'accessToken' in response_json['token']:
            # Retrieve the username
            username = response_json['user']['username']
            return {'accessToken': response_json['token']['accessToken'], 'username': username}
        else:
            print("Access token not in response: ", response_json)
            return None
    else:
        print("Error in authentication: ", response.status_code)
        print("Response text: ", response.text)
        return None


# Function to validate email address
def validate_email(email):
    # Simple regex for email validation
    email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b$'
    return bool(re.match(email_regex, email))

# Function to initialize JSON file
def initialize_file():
    # Check if the file exists, if not create it with an empty dictionary
    if not os.path.isfile("emails.json"):
        with open("emails.json", "w") as file:
            json.dump({}, file)

# Command handler for /start command
def start(update: Update, context: CallbackContext) -> int:
    username = update.message.from_user.username
    with open("emails.json", "r") as file:
        data = json.load(file)
    if username in data and 'accesstoken' in data[username]:
        update.message.reply_text('You are already logged in.')
        return TOKEN
    else:
        update.message.reply_text('Please enter your Myriad email:')
        return EMAIL

# Message handler for EMAIL state
def email(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    username = update.message.from_user.username
    if not validate_email(user_input):
        update.message.reply_text("The input is not a valid email. Please try again.")
        return EMAIL
    else:
        # We'll save the email locally by writing it to a JSON file
        with open("emails.json", "r") as file:
            data = json.load(file)
        if username not in data:
            data[username] = {'email': user_input}
        with open("emails.json", "w") as file:
            json.dump(data, file)
        update.message.reply_text(f"Email saved: {user_input}")
        send_magic_link(user_input, username, update, context)
        return MAGIC_LINK


# Message handler for TOKEN state
def token(update: Update, context: CallbackContext) -> int:
# ...
    response = authenticate(auth)
    if response is not None:
        accesstoken = response['accessToken']
        myriad_username = response['username']
        with open("emails.json", "r") as file:
            data = json.load(file)
        if username in data:
            data[username]['accesstoken'] = accesstoken
            data[username]['myriad_username'] = myriad_username  # Save the Myriad username
        with open("emails.json", "w") as file:
            json.dump(data, file)
        update.message.reply_text("You are now logged in!")
    else:
        update.message.reply_text("Authentication failed. Please try again.")
    return ConversationHandler.END

def handle_text(update: Update, context: CallbackContext):
    print("Entering handle_text()")
    
    username = update.message.from_user.username
    if is_user_logged_in(username):
        return post(update, context)
    else:
        update.message.reply_text("You're not logged in. Please use the /start command to log in.")


# Message handler for cancellation
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

def main():
    initialize_file()

    # Replace YOUR_API_KEY with your actual API key
    updater = Updater("x:xxx")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            EMAIL: [MessageHandler(Filters.text & ~Filters.command, email)],
            MAGIC_LINK: [MessageHandler(Filters.text & ~Filters.command, magic_link)],
            TOKEN: [MessageHandler(Filters.text & ~Filters.command, post)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()
