#!/usr/bin/python  
  
import httplib2  
import os  
import random  
import sys  
import time  
  
from apiclient.discovery import build  
from apiclient.errors import HttpError  
from apiclient.http import MediaFileUpload  
from oauth2client.client import flow_from_clientsecrets  
from oauth2client.file import Storage  
from oauth2client.tools import argparser, run_flow  
  
# Explicitly tell the underlying HTTP transport library not to retry, since  
# we are handling retry logic ourselves.  
httplib2.RETRIES = 1  
  
# Maximum number of times to retry before giving up.  
MAX_RETRIES = 10  
  
# Always retry when these exceptions are raised.  
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib2.ServerNotFoundError)  
  
# Always retry when an apiclient.errors.HttpError with one of these status  
# codes is raised.  
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]  
  
# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains  
# the OAuth 2.0 information for this application, including its client_id and  
# client_secret.  
CLIENT_SECRETS_FILE = "./client_secret.json"  
  
# This OAuth 2.0 access scope allows an application to upload files to the  
# authenticated user's YouTube channel, but doesn't allow other types of access.  
# YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"  
SCOPES = ['https://www.googleapis.com/auth/youtube.upload',  
          'https://www.googleapis.com/auth/youtube',  
          'https://www.googleapis.com/auth/youtubepartner']  
YOUTUBE_API_SERVICE_NAME = "youtube"  
YOUTUBE_API_VERSION = "v3"  
  
# This variable defines a message to display if the CLIENT_SECRETS_FILE is  
# missing.  
MISSING_CLIENT_SECRETS_MESSAGE = f"""  
WARNING: Please configure OAuth 2.0  
  
To make this sample run you will need to populate the client_secrets.json file  
found at:  
  
   {os.path.abspath(os.path.join(os.path.dirname(__file__), CLIENT_SECRETS_FILE))}  
  
with information from the API Console  
https://console.cloud.google.com/  
  
For more information about the client_secrets.json file format, please visit:  
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets  
"""  
  
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")  
  
  
def get_authenticated_service():
    """    Get an authenticated service for the YouTube API.

    This function retrieves the necessary credentials and builds an authenticated service for the YouTube API.

    Returns:
        A built authenticated service for the YouTube API.

    Raises:
        SomeException: An exception raised when some specific condition is met.
    """
  
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, 
                                   scope=SCOPES, 
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)  
  
    storage = Storage(f"{sys.argv[0]}-oauth2.json")  
    credentials = storage.get()  
  
    if credentials is None or credentials.invalid:  
        flags = argparser.parse_args()  
        credentials = run_flow(flow, storage, flags)  
  
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,  
                 http=credentials.authorize(httplib2.Http()))  
  
  
def initialize_upload(youtube, options):
    """    Initialize the video upload process to YouTube.

    Args:
        youtube: An authorized instance of the `googleapiclient.discovery.Resource` class.
        options: A dictionary containing the following keys:
            - 'keywords' (str): Comma-separated keywords for the video.
            - 'title' (str): Title of the video.
            - 'description' (str): Description of the video.
            - 'category' (str): Category ID for the video.
            - 'privacyStatus' (str): Privacy status of the video.

    Returns:
        The result of the resumable upload process.
            
            This function initializes the video upload process to YouTube by preparing the necessary metadata and calling the API's videos.insert method to create and upload the video. It takes an authorized `youtube` instance and a dictionary of `options` including keywords, title, description, category, and privacy status for the video. If keywords are provided, they are split into a list. The video metadata is then constructed and passed to the videos.insert method along with the media file for upload. The result of the resumable upload process is returned.
    """
  
    tags = None  
    if options['keywords']:  
        tags = options['keywords'].split(",")  
  
    body = {  
        'snippet': {  
            'title': options['title'],  
            'description': options['description'],  
            'tags': tags,  
            'categoryId': options['category']  
        },  
        'status': {  
            'privacyStatus': options['privacyStatus']  
        }  
    }  
  
    # Call the API's videos.insert method to create and upload the video.  
    insert_request = youtube.videos().insert(  
        part=",".join(body.keys()),  
        body=body,  
        media_body=MediaFileUpload(options['file'], chunksize=-1, resumable=True)  
    )  
  
    return resumable_upload(insert_request)  
  
  
# This method implements an exponential backoff strategy to resume a  
# failed upload.  
def resumable_upload(insert_request):
    """    This method implements an exponential backoff strategy to resume a failed upload.

    Args:
        insert_request: The insert request for the upload.

    Returns:
        The response of the upload.

    Raises:
        HttpError: An error occurred during the HTTP request.
        Exception: An exception occurred during the upload process.
    """
  
    response = None  
    error = None  
    retry = 0  
    while response is None:  
        try:  
            print("Uploading file...")  
            status, response = insert_request.next_chunk()  
            if 'id' in response:  
                print(f"Video id '{response['id']}' was successfully uploaded.")  
                return response  
        except HttpError as e:  
            if e.resp.status in RETRIABLE_STATUS_CODES:  
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"  
            else:  
                raise  
        except RETRIABLE_EXCEPTIONS as e:  
            error = f"A retriable error occurred: {e}"  
  
        if error is not None:  
            print(error)  
            retry += 1  
            if retry > MAX_RETRIES:  
                raise Exception("No longer attempting to retry.")  
  
            max_sleep = 2 ** retry  
            sleep_seconds = random.random() * max_sleep  
            print(f"Sleeping {sleep_seconds} seconds and then retrying...")  
            time.sleep(sleep_seconds)  
  
  
def upload_video(video_path, title, description, category, keywords, privacy_status):
    """    Uploads a video to YouTube.

    Args:
        video_path (str): The path to the video file.
        title (str): The title of the video.
        description (str): The description of the video.
        category (str): The category of the video.
        keywords (str): The keywords associated with the video.
        privacy_status (str): The privacy status of the video.

    Returns:
        dict: The response from the upload process.

    Raises:
        HttpError: An HTTP error occurred during the upload process.
    """
    
    # Get the authenticated YouTube service  
    youtube = get_authenticated_service()    
      
    # Retrieve and print the channel ID for the authenticated user  
    channels_response = youtube.channels().list(mine=True, part='id').execute()    
    for channel in channels_response['items']:    
        print(f"Channel ID: {channel['id']}")  # This will print out the channel ID(s)  
      
    try:    
        # Initialize the upload process  
        video_response = initialize_upload(youtube, {    
            'file': video_path,  # The path to the video file  
            'title': title,    
            'description': description,    
            'category': category,    
            'keywords': keywords,    
            'privacyStatus': privacy_status    
        })    
        return video_response  # Return the response from the upload process  
    except HttpError as e:    
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")    
        raise e  # Re-raise the exception to handle it elsewhere  
