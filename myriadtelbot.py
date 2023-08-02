import json
import requests
import os
import re
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
callback_url = "https://app.myriad.social/login"
from datetime import datetime
from bs4 import BeautifulSoup

EMAIL, MAGIC_LINK, TOKEN = range(3)
# Base URL for the Myriad API
base_url = "https://api.myriad.social"

import urllib.parse
import html
from telegram import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from telegram import Message

def get_user_id(username, at):
    print("Entering get_user_id()")

    with open("emails.json", "r") as file:
        data = json.load(file)
    myriad_username = data[username]['myriad_username']  # Extract the Myriad username

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + at,
    }

    response = requests.get(f"https://api.myriad.social/users/{myriad_username}", headers=headers)
    if response.status_code == 200:
        user_data = json.loads(response.text)
        user_id = user_data.get("id")
        print(f"User ID: {user_id}")
        return user_id
    else:
        print(f"Error retrieving user ID: {response.status_code}")
        return None
        
import urllib.parse

def view_comments(update: Update, context: CallbackContext, post_id: str) -> None:
    print("Entering view_comments()")
    
    username = update.callback_query.from_user.username
    with open("emails.json", "r") as file:
        data = json.load(file)
    at = data[username]['accesstoken']
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + at,
    }
    print(f"{base_url}/user/comments?postId={post_id}")
    api_endpoint = f"{base_url}/user/comments?postId={post_id}"

    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        comments_data = response.json()
        comments = comments_data.get("data", [])
        if comments:
            for comment in comments:
                text = comment.get("text")
                update.callback_query.message.reply_text(text)
        else:
            update.callback_query.message.reply_text("No comments found for this post.")
    else:
        print(f"Error retrieving comments: {response.status_code}")

def upvote(update: Update, context: CallbackContext, post_id):
    print("Entering upvote()")


    username = update.callback_query.from_user.username
    with open("emails.json", "r") as file:
        data = json.load(file)
    at = data[username]['accesstoken']

    user_id = get_user_id(username, at)  # Get the user ID
    if user_id is None:
        print("Upvote failed: Could not retrieve user ID.")
        return


    url = "https://api.myriad.social/user/votes"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + at,
    }
    data = {
        "type": "post",
        "referenceId": post_id,  # Assuming the post ID can be used as the reference ID
        "postId": post_id,
        "state": True,
        "userId": user_id
    }
    response = requests.post(url, headers=headers, json=data)

    print(f"Response status code: {response.status_code}")
    print(f"Response body: {response.text}")

    if response.status_code == 200:
        print("Upvote successful")
    else:
        print("Upvote failed")


def m_view(update: Update, context: CallbackContext, content=None) -> int:
    if content is None:
        content = context.args if context.args else update.message.text.split(' ', 1)[1:]

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
    message_to_send = update.message if update.message else update.callback_query.message
    for i, post in enumerate(posts, start=1):
        user = post['user']['name']
        text = parse_post(post)  # Parse the post here  # Parse the content here
        message = f"{i}. {user}: {text}\n\n"  # Create message for each post

        # Create an inline keyboard with "thumbs up" and "thumbs down" buttons
        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f'upvote'),
                #InlineKeyboardButton("View Comments", callback_data=f'view_comments {post["id"]}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_to_send.reply_text(message.strip(), reply_markup=reply_markup, parse_mode=ParseMode.HTML)  # Send each post as a separate message

    return TOKEN




def create_comment(update: Update, post_id: str, comment_text: str) -> None:
    url = 'https://api.myriad.social/user/comments'
    
    # Get the access token and Myriad username from the JSON file
    username = update.message.from_user.username
    with open("emails.json", "r") as file:
        data = json.load(file)
    access_token = data[username]['accesstoken']
    myriad_username = data[username]['myriad_username']

    payload = {
        "text": comment_text,
        "type": "comment",
        "section": "discussion",
        "referenceId": post_id,  # If this field is necessary, use the post_id as its value
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "userId": myriad_username,
        "postId": post_id
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token,
    }

    # Print payload and headers for debugging
    print(f"Request Payload: {json.dumps(payload, indent=4)}")
    print(f"Request Headers: {json.dumps(headers, indent=4)}")

    response = requests.request("POST", url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code} from Myriad API.")
        print(f"Response: {response.text}")
        return

    print("Comment created successfully!")
    update.message.reply_text("Comment created successfully!")

def parse_content(content):
    parsed_content = ""
    images = []
    embed_links = []

    if '<' in content and '>' in content:
        soup = BeautifulSoup(content, features="html.parser")
        for img in soup.find_all('img', src=True):
            image_link = f'<a href="{img["src"]}">Image</a>'
            images.append(image_link)
        for iframe in soup.find_all('iframe', src=True):
            url = iframe['src']
            embed_links.append(url)
        for tag in soup(["script", "style", "img", "iframe"]):
            tag.extract()
        parsed_content = soup.get_text(separator="\n")
        parsed_content = parsed_content.replace('&nbsp;', ' ')
    elif content.startswith('{') and content.endswith('}') or content.startswith('[') and content.endswith(']'):
        try:
            json_content = json.loads(content)
        except json.JSONDecodeError:
            return content, [], []
        if isinstance(json_content, list):
            for item in json_content:
                if 'type' in item and item['type'] == 'p' and 'children' in item:
                    for child in item['children']:
                        if 'text' in child:
                            parsed_content += child['text'] + '\n'
    else:
        parsed_content = content
    parsed_content = parsed_content.strip()
    return parsed_content, images, embed_links


def parse_post(post):
    title = post.get('title', '')
    post_id = post.get('id')
    post_url = f"https://app.myriad.social/post/{post_id}"
    text = post.get('text', '')

    parsed_text, images, embed_links = parse_content(text)
    metrics = post.get('metric', {})
    upvotes = metrics.get('upvotes', 0)
    downvotes = metrics.get('downvotes', 0)
    debates = metrics.get('debates', 0)
    discussions = metrics.get('discussions', 0)
    tips = metrics.get('tips', 0)
    formatted_metrics = f"⬆️: {upvotes} | ⬇️: {downvotes} | ❌: {debates} | 💬: {discussions} | 🪙: {tips}"

    result = ''
    if title:
        result += f"Title: {title}\n"
    if parsed_text:
        result += f"Text: {parsed_text}\n"
    for img in images:
        result += "\n" + img
    for link in embed_links:
        result += "\n" + link
    result += f"\nURL: {post_url}\n"  # The post URL is always at the end
    result += f"Metrics: {formatted_metrics}\n"

    return result.strip()

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
        m_view(update, context, ["1"])  
    else:
        update.message.reply_text(f"Error importing post: {response.status_code}")
        if response.status_code == 409:
            update.message.reply_text(f"Post may have already been imported.")
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
        m_view(update, context, ["1"])  
    else:
        update.message.reply_text(f"Error creating post: {response.status_code}")
        print(f"Error creating post: {response.status_code}")

    return TOKEN
    
    
def m_post(update: Update, context: CallbackContext) -> int:
    if context.args:  # If the command is used with a slash
        content = context.args
    else:  # If the command is used without a slash
        content = update.message.text.split(' ')[1:]  # Split the message text and exclude the command

    if content:  # Check if there is any content
        content = ' '.join(content).split('\n\n')  # Join the content into a single string before splitting
        content = [c.strip() for c in content if c.strip()]  # Remove whitespace-only strings
        if not content:  # Check if the content is empty
            update.message.reply_text("Cannot create an empty post.")
            return TOKEN
        print(f"Post content: {content}")
        create_myriad_post(update, context, "My Post Title", content)
    else:
        update.message.reply_text("Cannot create an empty post.")
    return TOKEN

def m_import(update: Update, context: CallbackContext) -> int:
    if context.args:  # If the command is used with a slash
        content = context.args
    else:  # If the command is used without a slash
        content = update.message.text.split(' ')[1:]  # Split the message text and exclude the command

    if content:  # Check if there is any content
        # Extract the first URL in the content
        urls = re.findall(r'(https?://[^\s]+)', ' '.join(content))
        if urls:
            url = urls[0]
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc in ['twitter.com', 'www.twitter.com', 'reddit.com', 'www.reddit.com', 'x.com', 'www.x.com']:
                import_post(update, context, url)
 
            else:
                #update.message.reply_text("Invalid URL. Only URLs from twitter.com, reddit.com, and x.com are supported.")
                return TOKEN
        else:
            update.message.reply_text("No URL provided to import.")
    else:
        update.message.reply_text("No URL provided to import.")
    return TOKEN


def m_embed(update: Update, context: CallbackContext) -> int:
    if context.args:  # If the command is used with a slash
        content = context.args
    else:  # If the command is used without a slash
        content = update.message.text.split(' ')[1:]  # Split the message text and exclude the command

    if content:
        # Join the content into a single string before passing it to the embed function
        content_str = ' '.join(content)
        # Convert youtu.be links to youtube.com links
        content_str = re.sub(r'https?://youtu\.be/([a-zA-Z0-9_-]+)', r'https://www.youtube.com/watch?v=\1', content_str)
        embed(update, context, content_str)
    else:
        update.message.reply_text("No URL provided to embed.")
    return TOKEN

def nakedurl(update: Update, context: CallbackContext) -> int:
    url = update.message.text.strip()
    chat_type = update.message.chat.type
    
    # Convert youtu.be links to youtube.com links
    url = re.sub(r'https?://youtu\.be/([a-zA-Z0-9_-]+)', r'https://www.youtube.com/watch?v=\1', url)
    parsed_url = urllib.parse.urlparse(url)
    netloc = parsed_url.netloc

    # Pass the URL as part of context.args
    context.args = [url]
    if chat_type != 'private':
        print('Entered nakedurl(), but it is a group chat')
        return TOKEN
    elif netloc in ['twitter.com', 'www.twitter.com', 'reddit.com', 'www.reddit.com']:
        return m_import(update, context)
    elif netloc in ['youtube.com', 'www.youtube.com', 'twitch.tv', 'www.twitch.tv']:
        return m_embed(update, context)
    else:
        update.message.reply_text("Invalid URL. Only URLs from twitter.com, reddit.com, youtube.com, and twitch.tv are supported.")
        return TOKEN




import re

def post(update: Update, context: CallbackContext) -> int:
    print("Entering post()")
    command, *content = update.message.text.split(' ', 1)
    command = command.lower()
    # If the message is a reply
    if update.message.reply_to_message is not None:
        # Get the text of the replied message
        replied_text = update.message.reply_to_message.text
        # Get the last URL in the text
        urls = re.findall(r'(https?://[^\s]+)', replied_text)
        last_url = urls[-1] if urls else None
        # Extract the post ID from the URL
        if last_url and "app.myriad.social/post/" in last_url:
            post_id = last_url.split('/')[-1]
            print(f"Post ID: {post_id}")
            create_comment(update, post_id, update.message.text)
            # Here you can do whatever you want with the post ID
            return TOKEN

    # Check if the command is a URL
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.match(command):
        return nakedurl(update, context)
    chat_type = update.message.chat.type
    if chat_type != 'private':
        return TOKEN
    elif command == "post":
        return m_post(update, context)
    elif command == "import":
        return m_import(update, context)
    elif command == "embed":
        return m_embed(update, context)
    elif command == "view":
        #return m_view(update, context)
        viewbuttons(update,context)

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
        
        
# Function to get the state of a user
def get_user_state(username):
    # Load the JSON data from the file
    with open("emails.json", "r") as file:
        data = json.load(file)
    # Return the state of the user if it exists, otherwise return None
    return data[username].get('state', None) if username in data else None

        
# Function to set the state of a user
def set_user_state(username, state):
    # Load the JSON data from the file
    with open("emails.json", "r") as file:
        data = json.load(file)
    # Set the state of the user
    if username in data:
        data[username]['state'] = state
    # Save the data back to the file
    with open("emails.json", "w") as file:
        json.dump(data, file)
        
# Message handler for MAGIC_LINK state
def magic_link(update: Update, context: CallbackContext) -> int:
    magic_link = update.message.text
    username = update.message.from_user.username

    # Check if the user is in the MAGIC_LINK state
    if get_user_state(username) != 'MAGIC_LINK':
        update.message.reply_text("Unexpected magic link. Please start the login process with /start.")
        return ConversationHandler.END

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
            # Set the state of the user to TOKEN
            set_user_state(username, 'TOKEN')
        with open("emails.json", "w") as file:
            json.dump(data, file)
        update.message.reply_text("You are now logged in!")
        return TOKEN
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
        # Set the state of the user to MAGIC_LINK
        set_user_state(username, 'MAGIC_LINK')
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
        
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def instructions(update: Update, context: CallbackContext):
    if update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message

    message.reply_text(
        "Here are the commands you can use:\n\n"
        "1. /start: Logs you into the bot. You need to be logged in to use the other commands.\n"
        "2. /view or \"view\": Shows you the most recent posts.\n"
        "3. /post or \"post\": Allows you to create a new post. For example, \"post Happy Birthday!\" or \"/post Happy Birthday!\" will create a new post with the text \"Happy Birthday!\".\n"
        "4. /import or \"import\": Imports a post from Reddit or Twitter. For example, \"import URL\" or \"/import URL\" where URL is the link to the Reddit or Twitter post you want to import.\n"
        "5. /embed or \"embed\": Imports a video from YouTube or Twitch and allows you to add a caption. For example, \"embed caption URL caption2\" or \"/embed caption URL caption2\" where URL is the link to the YouTube or Twitch video you want to import, and \"caption caption2\" is the caption you want to add to the post.\n"
        "6. Replying to any Myriad post shown on Telegram will let you comment on that post!\n\n"
        "Additionally, if you send a URL to the bot without any command, the bot will automatically check if the URL is from Reddit, Twitter, YouTube, or Twitch. If it is, the bot will import the post or video without a caption.\n\n"
        "Remember, you can always type /instructions to see these instructions again. Enjoy using the Myriad Social Telegram bot!"
    )

def viewbuttons(update: Update, context: CallbackContext):
    if update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message

    keyboard = [
        [
            InlineKeyboardButton("1", callback_data='view_posts 1'),
            InlineKeyboardButton("5", callback_data='view_posts 5'),
            InlineKeyboardButton("10", callback_data='view_posts 10'),
            InlineKeyboardButton("20", callback_data='view_posts 20'),
            InlineKeyboardButton("25", callback_data='view_posts 25'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message.reply_text('How many recent posts would you like to see?', reply_markup=reply_markup)

# Command handler for /start command
def start(update: Update, context: CallbackContext) -> int:
    username = update.message.from_user.username
    chat_type = update.message.chat.type

    if not username:
        update.message.reply_text('Sorry, the Myriad bot requires you to have set a Telegram @username. Please go to your Telegram settings to set a @username of your own. After you have done so, you may press /start again.')
        return

    with open("emails.json", "r") as file:
        data = json.load(file)

    if username in data and 'accesstoken' in data[username]:
        keyboard = [[InlineKeyboardButton("Instructions", callback_data='instructions'), InlineKeyboardButton("View Posts", callback_data='viewbuttons')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('You are already logged in. If you don\'t remember the commands, click the "Instructions" button. If you want to view posts, click the "View Posts" button.', reply_markup=reply_markup)
        return TOKEN
    elif chat_type != 'private':
        update.message.reply_text('Please send the /start command in a private message to the bot to log in.')
    else:
        update.message.reply_text("Hi, I am the official <a href='https://myriad.social'>Myriad Social</a> Telegram bot!", parse_mode=ParseMode.HTML)
        update.message.reply_text(f'{username}, let me check if you are already logged in.')
        update.message.reply_text("You are not logged in! If you have not created an account yet, create an account <a href='https://app.myriad.social/login?instance=https%3A%2F%2Fapi.myriad.social'>here</a>.", parse_mode=ParseMode.HTML)
        update.message.reply_text("If you have a Myriad account, but have not activated email login, click <a href='https://app.myriad.social/settings?section=email&instance=https%3A%2F%2Fapi.myriad.social'>here</a>.", parse_mode=ParseMode.HTML)
        update.message.reply_text('If you already have a Myriad account connected to an email address, please enter that email below:')
        # Set the state of the user to EMAIL
        set_user_state(username, 'EMAIL')
        return EMAIL



        

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
        instructions(update,context)
        viewbuttons(update,context)
    else:
        update.message.reply_text("Authentication failed. Please try again.")
    return ConversationHandler.END

def handle_text(update: Update, context: CallbackContext):
    print("Entering handle_text()")
    
    username = update.message.from_user.username
    if is_user_logged_in(username):
        return post(update, context)
    else:
        print("You're not logged in. Please use the /start command to log in.")
        
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    command, *args = query.data.split(' ')
    if command == 'view_posts':
        m_view(update, context, args)
    elif command == 'upvote':
        message_text = query.message.text
        url_pattern = re.compile(r'https://app.myriad.social/post/(\w+)')
        match = url_pattern.search(message_text)
        if match:
            post_id = match.group(1)
            upvote(update, context, post_id)
        else:
            update.message.reply_text("No Myriad URL found in the message text.")
    elif command == 'view_comments':
        message_text = query.message.text
        url_pattern = re.compile(r'https://app.myriad.social/post/(\w+)')
        match = url_pattern.search(message_text)
        if match:
            post_id = match.group(1)
            view_comments(update, context, post_id)
        else:
            update.message.reply_text("No Myriad URL found in the message text.")
    elif command == 'instructions':
        instructions(update, context)
    elif command == 'viewbuttons':
        viewbuttons(update, context)


# Message handler for cancellation
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END
    
def main():
    initialize_file()

    # Replace YOUR_API_KEY with your actual Telegram API key (not the Myriad api key)
    updater = Updater("")

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
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('instructions', instructions))
    dispatcher.add_handler(CommandHandler('post', m_post))
    dispatcher.add_handler(CommandHandler('import', m_import))
    dispatcher.add_handler(CommandHandler('embed', m_embed))
    dispatcher.add_handler(CommandHandler('view', viewbuttons))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(CallbackQueryHandler(button))  # Add the CallbackQueryHandler directly to the dispatcher
    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()
