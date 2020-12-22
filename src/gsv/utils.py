# -*- coding: utf-8 -*-

import hashlib
import hmac
import base64
import urllib.parse as urlparse
import pandas as pd
import csv
import json


def sign_url(input_url=None, secret=None):
  """ 
      Sign a request URL with a URL signing secret.
      
      Args:
      input_url - The URL to sign
      secret    - Your URL signing secret
      
      Returns:
      The signed request URL

      Example Run:
      if __name__ == "__main__":
        input_url = "https://maps.googleapis.com/maps/api/streetview?size=600x300&pano=-ixdYSlXb3ngOiG-H5W4Mw&heading=0&pitch=0&fov=120&key=1232sedfsdsdfj"
        secret = r"dfgdfssd"
        print("Signed URL: " + sign_url(input_url, secret))

  """

  if not input_url or not secret:
    raise Exception("Both input_url and secret are required")

  url = urlparse.urlparse(input_url)

  # We only need to sign the path+query part of the string
  url_to_sign = url.path + "?" + url.query

  # Decode the private key into its binary format
  # We need to decode the URL-encoded private key
  decoded_key = base64.urlsafe_b64decode(secret)

  # Create a signature using the private key and the URL-encoded
  # string using HMAC SHA1. This signature will be binary.
  signature = hmac.new(decoded_key, str.encode(url_to_sign), hashlib.sha1)

  # Encode the binary signature into base64 for use within a URL
  encoded_signature = base64.urlsafe_b64encode(signature.digest())

  original_url = url.scheme + "://" + url.netloc + url.path + "?" + url.query

  # Return signed URL
  return original_url + "&signature=" + encoded_signature.decode("utf-8")


def get_unique_df(csv_file):
  """
  Get unique dataframe
  """
  df = pd.read_csv(csv_file).reset_index(drop=True)
  df.drop_duplicates(subset="pano_id", inplace=True)
  return df


def GET_API_AND_SECRET_KEY(env_json_file):
  """
  Function to get env variables from json file

  Args:
    env_json_file   : path of file
  
  Returns:
    Json Object
  """
  with open(env_json_file, 'r') as myfile:
      data=myfile.read()

  # parse file
  obj = json.loads(data)

  return obj