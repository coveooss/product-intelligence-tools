# External
import json

# Performs and parses Coveo REST API calls.
# Before calling any function (class or instance), you must defines the class variables
# Api._platformURL, Api._uaURL, Api._orgId and Api._token.

class Api:
    # Create an instance that calls the platform API
    def __init__(self, target = 'platform'):
        match target:
            case 'platform':
                self.baseUrl = '{platformUrl}rest/'.format(platformUrl = Api._platformURL)
            case 'ua':
                self.baseUrl = '{platformUrl}rest/ua/v15/'.format(platformUrl = Api._platformURL)
            case 'analytics':
                self.baseUrl = '{uaUrl}rest/ua/v15/'.format(uaUrl = Api._uaURL)
            case _: # default
                raise ValueError # Undefined target
        self.orgId = Api._orgId
        self.token = Api._token
    
    # Call the API endpoint, using method (eg 'GET'), with the contentType and bodyData.
    # Return:
    #   If the returned status code is not in allowedStatusCodes, return False.
    #   Else return the API JSON response.
    def call(self, endpoint, method, contentType = None, bodyData = None, allowedStatusCodes = [200]):
        # Note that if an input to format() is not in the target string (eg endpoint does not have an {orgId} parameter)
        # then that input is safely and silently ignored.
        url = self.baseUrl + endpoint.format(orgId = self.orgId)
        header = {'Authorization': 'Bearer {}'.format(self.token)}
        if contentType is not None:
            header['Content-Type'] = contentType

        import requests
        match method.upper():
            case 'GET':
                response = requests.get(url,
                  headers = header
                )
            case 'POST':
                response = requests.post(url,
                  headers = header,
                  data = json.dumps(bodyData)
                )
            case 'PUT':
                response = requests.put(url,
                  headers = header,
                  data = json.dumps(bodyData)
                )
            case 'DELETE':
                response = requests.delete(url,
                      headers = header
                )
            case _: # Default
                raise ValueError('Unknown method ' + str(method))
        
        if(response.status_code not in allowedStatusCodes):
            errorCode = 'no errorCode'
            if response.text != '':
                errorCode = str(response.json().get('errorCode', 'no errorCode'))
            print('ERROR ' + str(response.status_code) + ' ' + str(errorCode) + ' from ' + str(url))
            return False
        if response.text == '': # Empty success response
            return True
        return json.loads(response.text)

    # Call an API endpoint that returns paginated responses.
    #   arrayKey is the response's key for the current results array; if None, then the response itself is the current array.
    #   pageCountKey is the response's key for the total number of pages; if None, then the response does not include a total count.
    #   pageParam is the name of the request's current page parameter (in bodyData, or as a query parameter if bodyData is None).
    # All other inputs are the same as call().
    # Returns the total response (all pages collected together).
    def callPaged(self, endpoint, method, arrayKey = None, pageCountKey = None, pageParam = 'page', startPage = 0, contentType = None, bodyData = None, allowedStatusCodes = [200]):
        e = endpoint
        currPageNum = startPage
        currResponse = None # One API call's response, will be set later
        totalResponse = []
        
        def getCurrArray():
            return currResponse if arrayKey is None else currResponse[arrayKey]

        # While first iteration OR
        # (no total page count, so iterate while results remain) OR 
        # (iterate until you reach total page count)
        while currPageNum == startPage or \
          (pageCountKey is None and len(getCurrArray()) > 0) or \
          (pageCountKey is not None and currPageNum < currResponse[pageCountKey]):

            # Inject currPageNum into API call
            if bodyData is None:
                e = endpoint + '&' + pageParam + '=' + str(currPageNum)
            else:
                bodyData[pageParam] = int(currPageNum)

            # Make the API call, get one page of results
            currResponse = self.call(e, method, contentType, bodyData, allowedStatusCodes)
            if currResponse == False:
                return False
            
            totalResponse.extend(getCurrArray()) # Accumulate results
            currPageNum = currPageNum + 1
        return totalResponse