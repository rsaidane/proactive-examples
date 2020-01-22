#!/usr/bin/env python3

import os, sys, bz2, uuid, pickle, json, connexion, wget
import pandas as pd
import numpy as np

from joblib import load
from binascii import hexlify
from flask_cors import CORS

# models folder
UPLOAD_MODELS_FOLDER = "model_as_a_service"

# load default model
DEFAULT_MODEL_FILE = os.path.join(UPLOAD_MODELS_FOLDER, 'final_model.pkl')
global SERVICE_CONFIG

# api key
API_KEY = hexlify(os.urandom(16)).decode() # str(uuid.uuid4())
# tokens
TOKENS = {
  'user'  : API_KEY
}

# get token api
def get_token_api() -> str:
  user = connexion.request.form["user"]
  token = TOKENS.get(user)
  if not token:
    return "Invalid user"
  else:
    print('Your token is: {uid}'.format(uid=token))
    return token

# predict api
def predict_api(data: str):
  api_token = data['api_token']
  result = ""
  if api_token == API_KEY:
    dataframe_json = data['dataframe_json']
    dataframe = pd.read_json(dataframe_json, orient='values')
    predictions = predict(dataframe)
  return json.dumps(list(predictions))

def predict(dataframe):
  global SERVICE_CONFIG
  SERVICE_CONFIG = {
    "model": load(DEFAULT_MODEL_FILE)
  }
  model = SERVICE_CONFIG['model']
  print("model:\n", model)
  print("dataframe:\n", dataframe)
  predictions = model.predict(dataframe.values)
  return predictions

# deploy api
def deploy_api() -> str:
  api_token = connexion.request.form["api_token"]
  if api_token == API_KEY:
    modelfile = connexion.request.files['modelfile']
    print("modelfile:\n", modelfile)
    model_id = "final_model"
    filename = model_id + ".pkl"
    model_file_path = os.path.join(UPLOAD_MODELS_FOLDER, filename)
    print("model_file_path:\n", model_file_path)
    modelfile.save(model_file_path)
    return "Model deployed"
  else:
    return "Invalid Token"

def load_model(model_file_path):
  import pickle 
  global SERVICE_CONFIG
  SERVICE_CONFIG = {
    "model": load(DEFAULT_MODEL_FILE)
  }
  model = pickle.load(open(model_file_path,'rb'))
  SERVICE_CONFIG['model'] = model
  print("model:\n", model)

# main
if __name__ == '__main__':
  app = connexion.FlaskApp(__name__, port=9090, specification_dir='/model_as_a_service')
  CORS(app.app)
  app.add_api('ml_service_swagger.yaml', arguments={'title': 'Machine Learning Model Service'})
  app.run(ssl_context=('/model_as_a_service/certificate_mas.pem', '/model_as_a_service/key_mas.pem'))