# External
import json

# Performs and parses Coveo REST API calls.
# Before calling any class function, you must defines the class variables
# Api._platformURL, Api._orgId and Api._token.

class Api:
    def call(endpoint, method, contentType = None, bodyData = None, allowedStatusCodes = [200]):
        # Note that if an input to format() is not in the target string (eg endpoint does not have an {orgId} parameter)
        # then that input is safely and silently ignored.
        url = '{platformUrl}rest/'.format(platformUrl = Api._platformURL) + endpoint.format(orgId = Api._orgId)
        header = {'Authorization': 'Bearer {}'.format(Api._token)}
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

    # This function is for endpoints that return a paginated array.
    # It keeps retrieving each page and accumulating the results, then returns them.
    def callPaginated(endpoint, method, contentType = None, bodyData = None, allowedStatusCodes = [200]):
        e = endpoint + '&page='
        totalResponse = []
        currResponse = []
        currPage = 0
        while currPage == 0 or len(currResponse) > 0:
            currResponse = Api.call(e + str(currPage), method, contentType, bodyData, allowedStatusCodes)
            if currResponse == False:
                return False
            totalResponse.extend(currResponse)
            currPage = currPage + 1
        return totalResponse
    
    # This function is for endpoints that return a paginated array wrapped in a dict.
    # It keeps retrieving each page and accumulating the results, then returns them as an array.
    #   arrayKey is the key of the returned array.
    #   pageCountKey is the key of the total number of pages.
    def callPaginatedWrapped(endpoint, method, arrayKey, pageCountKey, contentType = None, bodyData = None, allowedStatusCodes = [200]):
        e = endpoint
        totalResponse = []
        currResponse = {arrayKey: [], pageCountKey: 1}
        currPage = 0
        while currPage < currResponse[pageCountKey]:
            if bodyData is None:
                e = endpoint + '&page=' + str(currPage)
            else:
                bodyData['page'] = int(currPage)
            currResponse = Api.call(e, method, contentType, bodyData, allowedStatusCodes)
            if currResponse == False:
                return False
            totalResponse.extend(currResponse[arrayKey])
            currPage = currPage + 1
        return totalResponse