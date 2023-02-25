from functools import lru_cache, reduce
import json
from flask import Flask, request

app = Flask(__name__)

'''
- Whenever the application starts, it loads the whole swagger API schema on the memory and create all the API endpoints accordingly
- This microservice is used as a proxy for both request and response from the desired microservice
- Requests are analysed to check if the types of the input parameters match the data type on the input field, if not returns 403 and does not passes to the relevant microservice
- If everything checks out on the request, sends the request to the relevant microservice
- Response of the microservice is validated by this tool checking the proper response on the different fields taking a reference from the swagger API documentation
- If everything checks out the response is sent back to the client
- If there are any errors on the response returned by the microservice, it sends the generic output
'''




# Create a function which loads read only files and caches in the memory
# Caching can be implemented for ro files but is not needed for this particular case as only one file is loaded once
# @lru_cache(maxsize=2)
def read_file(filename: str):
    try:
        f  = open(filename,'r').readlines()
        return f
    except Exception as e:
        print(f"Unable to read file : {e}")

# api.json loaded as global variable
swagger_api = json.loads(''.join(read_file("api.json")))
valid_endpoints = swagger_api["paths"].keys()


# Replace multiple `/` characters in the URL recursively so that we can match to the keys on swagger API
def replace_multiple_slashes(url:str):
    if not url:
        return url
    if "//" not in url:
        return url
    return replace_multiple_slashes(url.replace("//", "/"))



# If endpoint exists, we have to parse the content of the swagger api for different HTTP Methods
# All the values of the endpoints are cached so that no need to run the function multiple times for same input
@lru_cache(maxsize=None)
def parse_swaggger(endpoint: str,  method: str):
    # Check if the parameter exists on swagger documentation
    tmp_swagger_api = swagger_api['paths'][endpoint][method]

    # Sample Response : {'name': ['id', 'message'], 'required': [True, True], 'type': ['int', 'str']}
    return reduce(lambda x, y: {
        "name": x["name"] + [y["name"]],
        "required": x["required"] + [y["required"]],
        "type": x["type"] + [ types[y["type"].lower()] ]
    }, tmp_swagger_api["parameters"], {"name": [], "required": [], "type": []})


def check_request_params(input_data, swagger_data):
    # Check if all the parameters match perfectly else we need to check if the required parameters are at least present
    ## All of the keys on input_data match on swagger_data
    if input_data == swagger_data['name']:
        return True
    
    # Extract parameters that are required: required=true and check if they are present on input data
    required_params = [ x[0] for x in list(filter( lambda pair: pair[1] and pair[0],  zip(swagger_data['name'], swagger_data['required'])   )) ]
    # for params in required_params:
    #     if params not in input_data:
    #         return False
    return all( param in input_data for param in required_params )


# Validating the input 
def is_int(n):
    return n.isdigit()

def is_float(n):
    try:
        return True if float(n) else False
    except ValueError:
        return False

def is_string(n):
    return isinstance(n, str)

# Map the data types to a function for validating the content
# Used on parse_swaggger function
types = {

        "integer" : is_int,
        "real" : is_float,
        "string" : is_string,
        "float" : is_float

}



@app.route('/test/<path:url>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def validate_input(url):
    # Sanitize URL parameter
    url = replace_multiple_slashes('/' + url)
    if url not in valid_endpoints:
        return '404'
    
    # Get all the variables on GET/POST Methods
    data = {}
    method = ''
    if request.method == 'GET':
        data = request.args.to_dict()
        method = 'get'
    elif request.method == 'POST':
        data = request.form.to_dict()
        method = 'post'
    
    # Check if the method exists on swagger documentation else return
    if  method not in swagger_api['paths'][url].keys():
        return "Method Not Supported"
    
    # Fetch the data from swagger for the particular endpoint and method
    swagger_data = parse_swaggger(url , method)

    # Match the input from the request to the swagger values
    # Check if all the required values are present
    # We can check if there are values that are not specified on the swagger documentation - Invalid Request???
    if not check_request_params( list(data.keys()), swagger_data): 
        return "Parameters check failed" 

    # Check if the parameters have the value as specified by the swagger documentation

    data_type = dict( zip( swagger_data["name"] , swagger_data["type"]  )  )

    if not all( [ data_type[key](value) for key,value in data.items() ] ):
        return "Mismatch data types"

    # Making an actual request to the server

    # Storing the response

    # Validating the response with the swagger json

    # Returning the hardcoded response if the above validating fails

    return f"Path is {url}"



if __name__ == '__main__':
    app.run()


