import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect

# Replace with your app's credentials
APP_KEY = "ffvn31gykfv9fgj"
APP_SECRET = "sm3ysm1x2jb6hsq"

# Create the OAuth2 flow
auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET, token_access_type="offline")

# Get the authorization URL
authorize_url = auth_flow.start()
print("1. Go to this URL in your browser:")
print(authorize_url)
print("\n2. Click 'Allow' (you might need to log in first).")
print("3. Copy the code provided by Dropbox and paste it below.")

# Ask user for the authorization code
auth_code = input("Enter the authorization code here: ").strip()

# Exchange the code for a refresh token
oauth_result = auth_flow.finish(auth_code)
print("\n✅ Success! Your refresh token is:")
print(oauth_result.refresh_token)
